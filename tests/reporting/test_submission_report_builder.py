from dataclasses import dataclass
from datetime import date, datetime

import pytest

from slim_domain.domain.customer.customer import Customer
from slim_domain.domain.tr.enums import ProcessingTime, RequestType
from slim_domain.domain.tr.tr_sample import TRSample
from slim_domain.domain.tr.tr_submission import TRSubmission

from slim_report_engine.reporting import column_widths, submission_report_builder as dispatcher


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
    metals_prep: str = ""
    metals_instrument: str = "ICPMS"


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
    _BY_ID = {101: _FakeElement(id=101, name="Antimony", symbol="Sb")}

    def get_by_symbol(self, symbol: str):
        return _FakeElement(id=0, name=symbol, symbol=symbol)

    def get_by_name(self, name: str):
        return next((e for e in self._BY_ID.values() if e.name == name), None)

    def load_element(self, element_id: int):
        return self._BY_ID.get(element_id)


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
    additional_element_ids=(),
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
        additional_element_ids=additional_element_ids,
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
    # Confirmed real (SetChemicalSheetName): tab name is the CHEMICAL
    # MATRIX, not the Sample ID -- both samples share "Test Acid" here,
    # so both get numbered "Test Acid 1"/"Test Acid 2".
    assert sheets[0].name == "Test Acid 1"
    assert sheets[1].name == "Test Acid 2"
    assert sheets[0].header_title == "Test Acid"
    # No more separate "A1" stamp -- the header preamble's own title row
    # sets column 1 of row 1 directly (see build_header_preamble).
    assert sheets[0].extra_cell_stamps == ()
    assert sheets[0].sections[0].id == "Header"
    assert sheets[0].sections[0].rows[0].get_value(1) == "Test Acid"


def test_generic_chemical_sample_string_stamped_into_every_section():
    """The behavior the user asked to confirm/fix: the standard
    "mmddyy-Chemical-Customer-SampleID" string (built the same way DM5/
    Wafer build theirs) lands in column 4 of EVERY REAL section's own
    "Sample Identification:" row -- not just the sheet's first real
    section, and not the header preamble (which has no such row at all)
    -- matching row_builders.py's "every section on a sheet shares it"
    framing."""
    samples = [_sample("S-001", analysis_ids=(1, 2), chemical_id=1, form_chemical_name="Test Acid Matrix")]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC", 2: "Alkalinity"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    expected = "030526-Test Acid Matrix-Acme Corp-S-001"
    real_sections = sheets[0].sections[1:]  # sections[0] is the header preamble
    assert len(real_sections) == 2
    for section in real_sections:
        assert section.rows[0].get_value(4) == expected


def test_water_sample_string_uses_the_literal_water_chemical_name():
    samples = [_sample("S-001", analysis_ids=(1,))]
    submission = _submission(samples, request_type=RequestType.WATER)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].sections[1].rows[0].get_value(4) == "030526-Water-Acme Corp-S-001"


def test_sample_with_multiple_independent_analyses_lands_on_one_sheet():
    """The behavior under test directly: a single physical sample
    requesting several independent analyses (here 36 Elements, TOC, and
    Alkalinity -- none of which combine like Conductivity+pH does) gets
    exactly ONE OutputSheet carrying all of their sections, not one
    sheet per analysis. Matches the real VBA architecture, which
    creates one new sheet per SAMPLE ROW and unions every requested
    analysis range onto that same sheet."""
    samples = [_sample("S-001", analysis_ids=(1, 2, 3), chemical_id=1)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements", 2: "TOC", 3: "Alkalinity"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )

    assert len(sheets) == 1  # one sheet total, not three
    assert sheets[0].name == "Test Acid"  # only sample with this chemical matrix -- no numeric suffix
    assert [s.id for s in sheets[0].sections] == ["Header", "36 Elements", "TOC", "Alkalinity"]


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
    assert len(sheets[0].extra_cell_stamps) == 1
    cell_address, value = sheets[0].extra_cell_stamps[0]
    assert cell_address == "D5"
    assert "NH4OH" in value


def test_dm5_composite_chemical_with_nothing_else_requested_gets_plain_panel():
    """End-to-end wiring check: the dispatcher resolves the sample's OTHER
    analysis selections and passes them to dm5_non_routine_report_builder
    -- confirmed real, a Composite chemical with no Anions/Titrations
    selected gets no anion block, no embedded Assay."""
    samples = [_sample("S-001", chemical_id=9)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL, customer_id=2)
    chemical_svc = _FakeChemicalService({9: _FakeChemical(id=9, name="0.49%HF")})
    sheets = dispatcher.build_submission_sheets(
        submission, _DM5N, chemical_svc, _FakeAnalysisService({}), _FakeElementService()
    )
    assert len(sheets[0].sections) == 1


def test_dm5_composite_chemical_with_anions_and_assay_requested_gets_both_blocks():
    samples = [_sample("S-001", analysis_ids=(1, 2), chemical_id=9)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL, customer_id=2)
    chemical_svc = _FakeChemicalService({9: _FakeChemical(id=9, name="0.49%HF")})
    analysis_svc = _FakeAnalysisService({1: "4 Anions", 2: "Assay"})
    sheets = dispatcher.build_submission_sheets(submission, _DM5N, chemical_svc, analysis_svc, _FakeElementService())
    assert len(sheets[0].sections) == 2
    assert sheets[0].sections[1].id == "0.49%HF_Assay"


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
    assert sheets[0].extra_cell_stamps == (("A1", "150mm Wafers"),)


def test_duplicate_chemical_matrix_gets_numbered_not_deduplicated_with_parens():
    """Confirmed real (SetChemicalSheetName): samples sharing a chemical
    matrix get "X 1"/"X 2" -- not the generic "(2)" collision suffix,
    which is now only a fallback for names _generic_tab_names didn't
    already handle."""
    samples = [
        _sample("S-001", analysis_ids=(1,), form_chemical_name="Same Name"),
        _sample("S-002", analysis_ids=(1,), form_chemical_name="Same Name"),
    ]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].name == "Same Name 1"
    assert sheets[1].name == "Same Name 2"


def test_generic_chemical_sheet_uses_standard_column_widths():
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].column_widths == column_widths.STANDARD


def test_dm5_sheet_uses_dm5_element_column_widths():
    samples = [_sample("S-001", chemical_id=9)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL, customer_id=2)
    chemical_svc = _FakeChemicalService({9: _FakeChemical(id=9, name="NH4OH")})
    sheets = dispatcher.build_submission_sheets(
        submission, _DM5N, chemical_svc, _FakeAnalysisService({}), _FakeElementService()
    )
    assert sheets[0].column_widths == column_widths.DM5_ELEMENT


def test_wafer_sheet_uses_wafer_column_widths():
    samples = [_sample("Slot-1", analysis_ids=(1,), reporting_units="atoms/cm^2", form_chemical_name="150mm")]
    submission = _submission(samples, request_type=RequestType.WAFER)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].column_widths == column_widths.WAFER


def test_chemical_sample_uses_the_resolved_chemicals_catalog_prep():
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    chemical_svc = _FakeChemicalService({1: _FakeChemical(id=1, name="Test Acid", metals_prep="ICPMS Digestion")})
    sheets = dispatcher.build_submission_sheets(submission, _CUSTOMER, chemical_svc, analysis_svc, _FakeElementService())
    footer = next(
        r for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1))
    )
    assert footer.get_value(1) == "Analysis by ICPMS (ICPMS Digestion)"


def test_chemical_sample_uses_the_resolved_chemicals_catalog_instrument():
    """Confirmed real: a very dirty/nasty matrix, or one that itself
    contains a metal (e.g. NaOH), gets its Chemical.metals_instrument
    manually set to ICPOES during the quote process."""
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    chemical_svc = _FakeChemicalService({1: _FakeChemical(id=1, name="Test Acid", metals_instrument="ICPOES")})
    sheets = dispatcher.build_submission_sheets(submission, _CUSTOMER, chemical_svc, analysis_svc, _FakeElementService())
    footer = next(r for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by" in str(r.get_value(1)))
    assert footer.get_value(1) == "Analysis by ICPOES (Evaporation)"


def test_chemical_sample_with_blank_catalog_instrument_defaults_to_icpms():
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    chemical_svc = _FakeChemicalService({1: _FakeChemical(id=1, name="Test Acid")})
    sheets = dispatcher.build_submission_sheets(submission, _CUSTOMER, chemical_svc, analysis_svc, _FakeElementService())
    footer = next(r for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by" in str(r.get_value(1)))
    assert "ICPMS" in footer.get_value(1)


def test_water_sample_always_uses_icpms_no_chemical_lookup():
    samples = [_sample("S-001", analysis_ids=(1,))]
    submission = _submission(samples, request_type=RequestType.WATER)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    footer = next(r for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by" in str(r.get_value(1)))
    assert "ICPMS" in footer.get_value(1)


def test_chemical_sample_with_blank_catalog_prep_defaults_to_evaporation():
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1)]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    chemical_svc = _FakeChemicalService({1: _FakeChemical(id=1, name="Test Acid")})  # metals_prep="" (blank)
    sheets = dispatcher.build_submission_sheets(submission, _CUSTOMER, chemical_svc, analysis_svc, _FakeElementService())
    footer = next(
        r for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1))
    )
    assert footer.get_value(1) == "Analysis by ICPMS (Evaporation)"


def test_water_sample_always_uses_dilute_and_shoot_no_chemical_lookup():
    samples = [_sample("S-001", analysis_ids=(1,))]
    submission = _submission(samples, request_type=RequestType.WATER)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    footer = next(
        r for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1))
    )
    assert footer.get_value(1) == "Analysis by ICPMS (Dilute and Shoot)"


def test_customer_additional_elements_prep_overrides_only_the_second_footer():
    """The customer-level flag, confirmed real: at least one customer's
    additional elements are run by a different method than their main
    panel. Deliberately customer-agnostic here -- any real customer's
    override value lives only in a real database record, never in this
    public repo (see Customer.additional_elements_prep, slim-domain)."""
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1, additional_element_ids=(101,))]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    chemical_svc = _FakeChemicalService({1: _FakeChemical(id=1, name="Test Acid", metals_prep="Evaporation")})
    customer_with_override = _CUSTOMER.model_copy(update={"additional_elements_prep": "Alternate Method"})
    sheets = dispatcher.build_submission_sheets(
        submission, customer_with_override, chemical_svc, analysis_svc, _FakeElementService()
    )
    footers = [
        r.get_value(1) for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1))
    ]
    assert footers == ["Analysis by ICPMS (Evaporation)", "Analysis by ICPMS (Alternate Method)"]


def test_customer_with_no_additional_elements_prep_override_uses_same_prep_both_times():
    samples = [_sample("S-001", analysis_ids=(1,), chemical_id=1, additional_element_ids=(101,))]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "36 Elements"})
    chemical_svc = _FakeChemicalService({1: _FakeChemical(id=1, name="Test Acid", metals_prep="Evaporation")})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, chemical_svc, analysis_svc, _FakeElementService()
    )
    footers = [
        r.get_value(1) for r in sheets[0].sections[1].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1))
    ]
    assert footers == ["Analysis by ICPMS (Evaporation)", "Analysis by ICPMS (Evaporation)"]


def test_sheet_names_sanitize_illegal_characters():
    samples = [_sample("S-001", analysis_ids=(1,), form_chemical_name="Chem:With/Illegal*Chars")]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    for ch in "[]:*?/\\<>|":
        assert ch not in sheets[0].name


def test_illegal_characters_are_removed_not_replaced_with_a_placeholder():
    """Confirmed real (RemoveIllegalCharacters' Case Else branch): illegal
    sheet-name characters are dropped entirely, not swapped for "_"."""
    samples = [_sample("S-001", analysis_ids=(1,), form_chemical_name="A:B/C")]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].name == "ABC"


def test_generic_tab_names_water_single_sample_has_no_number():
    samples = [_sample("S-001", analysis_ids=(1,))]
    submission = _submission(samples, request_type=RequestType.WATER)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].name == "Water"


def test_generic_tab_names_water_multiple_samples_all_numbered():
    samples = [
        _sample("S-001", analysis_ids=(1,)),
        _sample("S-002", analysis_ids=(1,)),
        _sample("S-003", analysis_ids=(1,)),
    ]
    submission = _submission(samples, request_type=RequestType.WATER)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert [s.name for s in sheets] == ["Water 1", "Water 2", "Water 3"]


def test_generic_tab_names_unique_chemical_matrix_gets_no_number():
    samples = [
        _sample("S-001", analysis_ids=(1,), form_chemical_name="PGME"),
        _sample("S-002", analysis_ids=(1,), form_chemical_name="IPA"),
    ]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert [s.name for s in sheets] == ["PGME", "IPA"]


def test_generic_tab_names_mixed_unique_and_duplicate_chemical_matrices():
    samples = [
        _sample("S-001", analysis_ids=(1,), form_chemical_name="NMP"),
        _sample("S-002", analysis_ids=(1,), form_chemical_name="PGME"),
        _sample("S-003", analysis_ids=(1,), form_chemical_name="NMP"),
    ]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert [s.name for s in sheets] == ["NMP 1", "PGME", "NMP 2"]


def test_generic_tab_names_truncates_chemical_matrix_to_28_chars_leaving_room_for_suffix():
    long_name = "A" * 40
    samples = [
        _sample("S-001", analysis_ids=(1,), form_chemical_name=long_name),
        _sample("S-002", analysis_ids=(1,), form_chemical_name=long_name),
    ]
    submission = _submission(samples, request_type=RequestType.CHEMICAL)
    analysis_svc = _FakeAnalysisService({1: "TOC"})
    sheets = dispatcher.build_submission_sheets(
        submission, _CUSTOMER, _FakeChemicalService(), analysis_svc, _FakeElementService()
    )
    assert sheets[0].name == "A" * 28 + " 1"
    assert sheets[1].name == "A" * 28 + " 2"
    assert len(sheets[0].name) <= 31
    assert len(sheets[1].name) <= 31
