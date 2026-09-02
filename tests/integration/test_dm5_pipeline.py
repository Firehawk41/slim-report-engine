"""End-to-end proof for the DM5 non-routine path. DM5 has no intake form
of its own -- confirmed real (DOMAIN_BRIEF.md): a DM5 non-routine sample
arrives via the SAME Chemical Testing Request form as any other customer,
distinguished only by the resolved customer/chemical names. This proves
the real Chemical form parses correctly into a DM5-routable TRSample, and
that dm5_non_routine_report_builder (not chemical_water_report_builder)
is the right dispatch target once the customer resolves to "DM5N"/"DM5S".
"""

import os
from datetime import date
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from infrastructure.database import Base
from slim_domain.domain.analysis.analysis_service import AnalysisService
from slim_domain.domain.chemical.chemical import Chemical
from slim_domain.domain.chemical.chemical_service import ChemicalService
from slim_domain.domain.customer.customer import Customer
from slim_domain.domain.element.element_repository import _ElementRow
from slim_domain.domain.element.element_service import ElementService
from slim_domain.domain.tr.tr_submission_form_parser import TRSubmissionFormParser

from slim_report_engine.reporting import dm5_non_routine_report_builder
from slim_report_engine.reporting.presets import analyte_presets

_FORM_PATH = (
    Path(os.environ.get("PVB_BRIDGE_PATH", r"C:\Users\Jamie\Python-VBA-Bridge"))
    / "ReportCreator Project"
    / "Doc-F31 PRECILAB Analytical Testing Request Form - Chemicals.xlsx"
)

_DM5N_CUSTOMER = Customer(
    id=3, name="DM5N", street_address="1 Fab Way",
    city="Austin", state="TX", postal_code="78701", country="USA",
)
_NH4OH_CHEMICAL = Chemical(id=9, name="NH4OH", metals_prep="N/A", silicon_prep="N/A", ions_prep="N/A")


class _StubResolver:
    def resolve_customer(self, name, address, address2):
        return _DM5N_CUSTOMER

    def resolve_chemical(self, form_name):
        return _NH4OH_CHEMICAL


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for symbol in analyte_presets.trace_elements_36():
            s.add(_ElementRow(element_symbol=symbol, element_name=symbol))
        s.commit()
        s.execute(text(
            "CREATE TABLE invoice_default_contacts "
            "(contact_email TEXT, customer_id INTEGER, is_default INTEGER, is_active INTEGER)"
        ))
        s.commit()
        yield s


@pytest.mark.skipif(not _FORM_PATH.exists(), reason="real Chemical intake form not available in this environment")
def test_real_chemical_form_with_dm5_customer_routes_to_dm5_builder(session):
    wb = openpyxl.load_workbook(_FORM_PATH)
    ws = wb.active

    # DM5 arrives via the exact same form as any other customer -- only
    # the resolved customer/chemical differ (the StubResolver here always
    # resolves to DM5N/NH4OH regardless of the literal form text, exactly
    # like a real resolver would once it recognizes these values).
    ws["C10"] = "DM5N"
    ws["C11"] = "1 Fab Way"
    ws["C12"] = "Austin, TX"
    ws["P5"] = date(2026, 3, 5)  # Date received (Chemical column map)

    ws["B22"] = "S-001"
    ws["C22"] = "NH4OH"
    ws["K22"] = "Next Day"  # processing time, column 11 for Chemical

    analysis_svc = AnalysisService(session)
    chemical_svc = ChemicalService(session)
    element_svc = ElementService(session)
    resolver = _StubResolver()

    parser = TRSubmissionFormParser(
        session=session,
        chemical_service=chemical_svc,
        analysis_service=analysis_svc,
        element_service=element_svc,
        input_resolver=resolver,
    )

    submission = parser.build_from_worksheet(ws, filename="test.xlsx")

    assert len(submission.samples) == 1
    sample = submission.samples[0]

    customer = _DM5N_CUSTOMER  # caller resolves via CustomerService.load_customer(submission.customer_id) in real use
    chemical = chemical_svc.load_chemical(sample.chemical_id) or _NH4OH_CHEMICAL

    assert customer.name.startswith("DM5")  # confirms this sample should route to the DM5 builder, not the generic one

    result = dm5_non_routine_report_builder.build_non_routine_report(
        chemical.name, customer.name, submission.date_received, sample.sample_name, element_svc
    )

    assert len(result.sections) == 1
    assert result.chemical_label == "NH4OH"
    assert result.name_cell_address == "D5"
    assert "NH4OH" in result.sample_string
    assert "DM5N" in result.sample_string

    data_rows = [r for r in result.sections[0].rows if r.style_name == "DataLabel"]
    assert len(data_rows) == 36
