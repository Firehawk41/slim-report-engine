from dataclasses import dataclass
from datetime import date, datetime

import pytest

from slim_domain.domain.customer.customer import Customer
from slim_domain.domain.tr.enums import ProcessingTime, RequestType
from slim_domain.domain.tr.tr_sample import TRSample
from slim_domain.domain.tr.tr_submission import TRSubmission

from slim_report_engine.reporting import submission_report_builder as dispatcher


@dataclass(frozen=True)
class _FakeAnalysis:
    name: str


class _FakeAnalysisService:
    def __init__(self, id_to_name: dict[int, str]) -> None:
        self._id_to_name = id_to_name

    def load_analysis(self, analysis_id: int):
        name = self._id_to_name.get(analysis_id)
        return _FakeAnalysis(name) if name is not None else None


@dataclass(frozen=True)
class _FakeChemical:
    id: int
    name: str


class _FakeChemicalService:
    def __init__(self, id_to_chemical: dict[int, _FakeChemical] | None = None) -> None:
        self._id_to_chemical = id_to_chemical or {}

    def load_chemical(self, chemical_id: int):
        return self._id_to_chemical.get(chemical_id)


@dataclass(frozen=True)
class _FakeElement:
    id: int
    name: str
    symbol: str


class _FakeElementService:
    def get_by_symbol(self, symbol: str):
        return _FakeElement(id=0, name=symbol, symbol=symbol)

    def load_element(self, element_id: int):
        return None


_CUSTOMER = Customer(
    id=1, name="Acme Corp", street_address="1 Main St",
    city="Springfield", state="IL", postal_code="62701", country="USA",
)
_DM5N = Customer(
    id=2, name="DM5N", street_address="1 Fab Way",
    city="Austin", state="TX", postal_code="78701", country="USA",
)


def _sample(
    name: str,
    analysis_ids=(),
    chemical_id: int = 0,
    processing_time=ProcessingTime.NEXT_DAY,
    reporting_units="",
    form_chemical_name="Test Acid",
) -> TRSample:
    return TRSample(
        sample_name=name,
        form_chemical_name=form_chemical_name,
        processing_time=processing_time,
        additional_notes="",
        requested_time="",
        chemical_id=chemical_id,
        analysis_ids=analysis_ids,
        reporting_units=reporting_units,
    )


def _submission(samples: list[TRSample], request_type=RequestType.CHEMICAL, customer_id=1) -> TRSubmission:
    return TRSubmission(
        customer_id=customer_id,
        date_submitted=date(2026, 3, 4),
        date_received=date(2026, 3, 5),
        request_type=request_type,
        customer_contact="Jane Doe",
        customer_phone="555-0100",
        po_information="",
        credit_card_information="",
        file_name="test.xlsx",
        service_date=date(1901, 1, 1),
        download_date=datetime(2026, 3, 5, 12, 0, 0),
        form_customer_name="Acme Corp",
        form_customer_address="",
        form_customer_address_2="",
        samples=tuple(samples),
    )


def test_generic_chemical_customer_one_sheet_per_sample():
    samples = [
        _sample("S-001", analysis_ids=(1,), chemical_id=1),
        _sample("S-002", analysis_ids=(1,), chemical_id=1),
    ]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert len(sheets) == 2
    assert sheets[0].name == "S-001"
    assert sheets[0].header_title == "Test Acid"
    assert sheets[0].sample_id_stamp is None


def test_water_customer_header_title_is_water():
    samples = [_sample("S-001", analysis_ids=(1,))]
    submission = _submission(samples, request_type=RequestType.WATER)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].header_title == "Water"


def test_dm5_customer_supported_chemical_routes_to_dm5_builder():
    samples = [_sample("S-001", chemical_id=9)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL, customer_id=2)
    chemical_svc = _FakeChemicalService({9: _FakeChemical(id=9, name="NH4OH")})
    sheets = dispatcher.build_submission_sheets(
        submission, _DM5N, chemical_svc, _FakeAnalysisService({}), _FakeElementService()
    )
    assert len(sheets) == 1
    assert sheets[0].name == "NH4OH"
    assert sheets[0].sample_id_stamp is not None
    cell_address, value = sheets[0].sample_id_stamp
    assert cell_address == "D5"
    assert "NH4OH" in value


def test_dm5_customer_unsupported_chemical_raises():
    samples = [_sample("S-001", chemical_id=9)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL, customer_id=2)
    chemical_svc = _FakeChemicalService({9: _FakeChemical(id=9, name="Not A Real DM5 Chemical")})
    with pytest.raises(ValueError, match="not one of the 21 chemicals"):
        dispatcher.build_submission_sheets(
            submission, _DM5N, chemical_svc, _FakeAnalysisService({}), _FakeElementService()
        )


def test_wafer_request_type_routes_to_wafer_builder_regardless_of_customer():
    samples = [_sample("Slot-1", analysis_ids=(1,), reporting_units="atoms/cm^2", form_chemical_name="150mm")]
    submission = _submission(samples, request_type=RequestType.WAFER)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert len(sheets) == 1
    assert sheets[0].header_title == "150mm Wafers"
    assert sheets[0].sample_id_stamp is None


def test_duplicate_sheet_names_get_deduplicated():
    samples = [
        _sample("Same Name", analysis_ids=(1,)),
        _sample("Same Name", analysis_ids=(1,)),
    ]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].name == "Same Name"
    assert sheets[1].name == "Same Name (2)"


def test_sheet_names_sanitize_illegal_characters():
    samples = [_sample("Sample:With/Illegal*Chars", analysis_ids=(1,))]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    for ch in "[]:*?/\\":
        assert ch not in sheets[0].name
