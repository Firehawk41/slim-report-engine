from dataclasses import dataclass

import pytest

from slim_domain.domain.tr.enums import ProcessingTime
from slim_domain.domain.tr.tr_sample import TRSample

from slim_report_engine.reporting import chemical_water_report_builder as orchestrator


@dataclass(frozen=True)
class _FakeAnalysis:
    name: str


class _FakeAnalysisService:
    """Maps analysis_id -> name via a plain dict, no DB session needed."""

    def __init__(self, id_to_name: dict[int, str]) -> None:
        self._id_to_name = id_to_name

    def load_analysis(self, analysis_id: int):
        name = self._id_to_name.get(analysis_id)
        return _FakeAnalysis(name) if name is not None else None


@dataclass(frozen=True)
class _FakeElement:
    name: str
    symbol: str


class _FakeElementService:
    """Resolves ANY symbol to an element named after itself -- good enough
    for dispatch tests, which only care that the right builder ran, not
    real periodic-table names. get_by_name/load_element resolve a small
    fixed catalog for the additional-elements tests specifically."""

    _BY_ID = {101: _FakeElement("Antimony", "Sb"), 102: _FakeElement("Arsenic", "As")}

    def get_by_symbol(self, symbol: str):
        return _FakeElement(name=symbol, symbol=symbol)

    def get_by_name(self, name: str):
        return next((e for e in self._BY_ID.values() if e.name == name), None)

    def load_element(self, element_id: int):
        return self._BY_ID.get(element_id)


def _footer_text(section):
    """Some analysis types have a confirmed real SOP mapping (see
    reporting/sop_codes.py), which inserts a "Test Methods: ..." row
    between the footer text and the trailing blank -- find the footer row
    by content instead of assuming it's always second-to-last."""
    return next(r.get_value(1) for r in section.rows if r.get_value(1) and "Analysis by" in str(r.get_value(1)))


def _sample(analysis_ids: tuple[int, ...], additional_element_ids: tuple[int, ...] = ()) -> TRSample:
    return TRSample(
        sample_name="S-1",
        form_chemical_name="Test Matrix",
        processing_time=ProcessingTime.NEXT_DAY,
        additional_notes="",
        requested_time="",
        chemical_id=1,
        analysis_ids=analysis_ids,
        additional_element_ids=additional_element_ids,
    )


# ---------------------------------------------------------------------------
# can_build_sections
# ---------------------------------------------------------------------------

def test_can_build_sections_false_for_no_analyses():
    svc = _FakeAnalysisService({})
    assert orchestrator.can_build_sections(_sample(()), svc) is False


def test_can_build_sections_true_for_all_supported():
    svc = _FakeAnalysisService({1: "36 Elements", 2: "TOC"})
    assert orchestrator.can_build_sections(_sample((1, 2)), svc) is True


def test_can_build_sections_false_for_any_unsupported():
    svc = _FakeAnalysisService({1: "36 Elements", 2: "Sn+2 Iodine Titration"})
    assert orchestrator.can_build_sections(_sample((1, 2)), svc) is False


def test_can_build_sections_true_for_standalone_ph():
    """The pH fix: standalone pH is supported now, not conditionally
    rejected like the VBA source."""
    svc = _FakeAnalysisService({1: "pH"})
    assert orchestrator.can_build_sections(_sample((1,)), svc) is True


def test_can_build_sections_true_for_dissolved_and_total_si():
    """The Silicon gap fix: CanBuildSections and BuildSections now agree."""
    svc = _FakeAnalysisService({1: "Dissolved and Total Si"})
    assert orchestrator.can_build_sections(_sample((1,)), svc) is True


# ---------------------------------------------------------------------------
# build_sections -- metals
# ---------------------------------------------------------------------------

def test_10_26_36_elements_all_use_the_same_36_symbol_list_different_labels():
    for name, expected_label in (("10 Elements", "10 Tr.Elts"), ("26 Elements", "26 Tr.Elts"), ("36 Elements", "36 Tr.Elts")):
        svc = _FakeAnalysisService({1: name})
        sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
        assert len(sections) == 1
        section = sections[0]
        data_rows = [r for r in section.rows if r.style_name == "DataLabel" and r.get_value(3)]
        assert len(data_rows) == 36
        avg_row = next(r for r in section.rows if r.get_value(2) and "AVERAGE" in str(r.get_value(2)))
        assert avg_row.get_value(2) == f"AVERAGE / {expected_label}"


def test_67_elements_uses_67_symbol_list():
    svc = _FakeAnalysisService({1: "67 Elements"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    data_rows = [r for r in sections[0].rows if r.style_name == "DataLabel" and r.get_value(3)]
    assert len(data_rows) == 67


# ---------------------------------------------------------------------------
# build_sections -- ions
# ---------------------------------------------------------------------------

def test_4_anions_panel_has_4_rows_labeled_anion():
    svc = _FakeAnalysisService({1: "4 Anions"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    section = sections[0]
    header = section.rows[1]
    assert header.get_value(2) == "Anion"
    data_rows = [r for r in section.rows if r.style_name == "DataLabel"]
    assert len(data_rows) == 4


def test_ion_panel_footer_bare_by_default_no_ions_prep_given():
    """Confirmed real (direct correction): most real ion panels have NO
    parenthesized prep at all -- only a chemical with its own real
    Chemical.ions_prep on file gets one (see ions_prep_text)."""
    svc = _FakeAnalysisService({1: "4 Anions"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService(), metals_prep_text="Evaporation")
    footer = next(r for r in sections[0].rows if r.get_value(1) and "Analysis by IC" in str(r.get_value(1)))
    assert footer.get_value(1) == "Analysis by IC"


def test_ion_panel_footer_includes_own_ions_prep_text_when_given():
    """Confirmed real (one real Chemical customer's 4-Anions report):
    "Analysis by IC (<prep>)" -- ions_prep_text is a SEPARATE catalog
    field from the metals panel's own prep, not reused from it."""
    svc = _FakeAnalysisService({1: "4 Anions"})
    sections = orchestrator.build_sections(
        _sample((1,)), svc, _FakeElementService(), metals_prep_text="Dilute and Shoot", ions_prep_text="Evaporation"
    )
    footer = next(r for r in sections[0].rows if r.get_value(1) and "Analysis by IC" in str(r.get_value(1)))
    assert footer.get_value(1) == "Analysis by IC (Evaporation)"


def test_4_anions_panel_has_confirmed_test_methods_row():
    """Confirmed real (cross-referenced against the intake form's own
    selection for a real sample) -- see sop_codes.ION_PANEL_SOP_CODES."""
    svc = _FakeAnalysisService({1: "4 Anions"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    test_methods = next(r for r in sections[0].rows if r.get_value(1) and "Test Methods" in str(r.get_value(1)))
    assert test_methods.get_value(1) == "Test Methods: PR-IN46 and PR-IN06."


def test_5_anions_panel_has_no_confirmed_test_methods_row():
    """No confirmed real SOP mapping for plain "5 Anions" -- only "4
    Anions" and "5 Anions + MS Authentication" were cross-referenced."""
    svc = _FakeAnalysisService({1: "5 Anions"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert not any("Test Methods" in str(r.get_value(1)) for r in sections[0].rows)


def test_gbp_panel_labeled_analyte():
    svc = _FakeAnalysisService({1: "GBP"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    header = sections[0].rows[1]
    assert header.get_value(2) == "Analyte"


# ---------------------------------------------------------------------------
# build_sections -- silicon
# ---------------------------------------------------------------------------

def test_total_silicon_alone():
    svc = _FakeAnalysisService({1: "Total Silicon"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    labels = [r.get_value(2) for r in sections[0].rows if r.style_name == "DataLabel"]
    assert labels == ["Silicon"]


def test_total_and_dissolved_silicon_collapse_into_one_section_with_colloidal_row():
    svc = _FakeAnalysisService({1: "Total Silicon", 2: "Dissolved Silicon"})
    sections = orchestrator.build_sections(_sample((1, 2)), svc, _FakeElementService())
    assert len(sections) == 1
    labels = [r.get_value(2) for r in sections[0].rows if r.style_name == "DataLabel"]
    assert labels == ["Silicon", "Dissolved Silica", "Colloidal Silica *"]


# ---------------------------------------------------------------------------
# build_sections -- electrical / pH fix
# ---------------------------------------------------------------------------

def test_conductivity_alone():
    svc = _FakeAnalysisService({1: "Conductivity"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    footer = sections[0].rows[-2]
    assert footer.get_value(1) == "Analysis by Conductivity Electrode"


def test_standalone_ph_dispatches_to_misc_analysis_not_electrical():
    """The pH fix under test: no Conductivity present -> Misc Analysis's
    own pH block, not the Electrical Testing one, and NOT a raise."""
    svc = _FakeAnalysisService({1: "pH"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    header = sections[0].rows[1]
    assert header.get_value(2) == "pH"  # Misc Analysis's category label, not "Electrical Testing"
    footer = sections[0].rows[-2]
    assert footer.get_value(1) == "Analysis by pH Electrode"


def test_conductivity_and_ph_together_collapse_into_one_electrical_section():
    svc = _FakeAnalysisService({1: "Conductivity", 2: "pH"})
    sections = orchestrator.build_sections(_sample((1, 2)), svc, _FakeElementService())
    assert len(sections) == 1
    header = sections[0].rows[1]
    assert header.get_value(2) == "Electrical Testing"
    footer = sections[0].rows[-2]
    assert footer.get_value(1) == "Analysis by pH/Conductivity Electrode"


def test_conductivity_and_ph_order_reversed_still_collapses_into_one_section():
    """Whichever of Conductivity/pH is processed first, the pair still
    collapses into exactly one section, not two."""
    svc = _FakeAnalysisService({1: "pH", 2: "Conductivity"})
    sections = orchestrator.build_sections(_sample((1, 2)), svc, _FakeElementService())
    assert len(sections) == 1
    assert sections[0].rows[1].get_value(2) == "Electrical Testing"


# ---------------------------------------------------------------------------
# build_sections -- misc analysis combine freely
# ---------------------------------------------------------------------------

def test_density_lpc_apha_combine_freely_with_no_special_logic():
    svc = _FakeAnalysisService({1: "Density", 2: "Liquid Particle Count", 3: "APHA Color"})
    sections = orchestrator.build_sections(_sample((1, 2, 3)), svc, _FakeElementService())
    assert len(sections) == 3
    footers = [_footer_text(s) for s in sections]
    assert footers == [
        "Analysis by Gay-Lussac Pycnometer",
        "Analysis by Liquid Particle Counter.",
        "Analysis by UV-Vis (average of six replicates)",
    ]


# ---------------------------------------------------------------------------
# ordering, dedup, and error path
# ---------------------------------------------------------------------------

def test_sections_preserve_first_requested_order():
    svc = _FakeAnalysisService({1: "TOC", 2: "Alkalinity", 3: "Bacteria Count"})
    sections = orchestrator.build_sections(_sample((1, 2, 3)), svc, _FakeElementService())
    assert [s.id for s in sections] == ["TOC", "Alkalinity", "Bacteria Count"]


def test_duplicate_analysis_ids_resolving_to_the_same_name_are_deduplicated():
    svc = _FakeAnalysisService({1: "TOC", 2: "TOC"})
    sections = orchestrator.build_sections(_sample((1, 2)), svc, _FakeElementService())
    assert len(sections) == 1


def test_unsupported_analysis_raises_clear_error():
    svc = _FakeAnalysisService({1: "Sn+2 Iodine Titration"})
    with pytest.raises(ValueError, match="Sn\\+2 Iodine Titration"):
        orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())


# ---------------------------------------------------------------------------
# build_sections -- Assay / Titrations (confirmed real: 3 different real
# Chemical customers' reports)
# ---------------------------------------------------------------------------

def test_assay_dispatches_to_titrations_builder():
    svc = _FakeAnalysisService({1: "Assay"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    assert _footer_text(sections[0]) == "Analysis by Auto-Titrator"


def test_can_build_sections_true_for_assay():
    svc = _FakeAnalysisService({1: "Assay"})
    assert orchestrator.can_build_sections(_sample((1,)), svc) is True


def test_gc_fid_dispatches_to_titrations_builder():
    """Confirmed real: a real Chemical customer's intake form uses
    "GC-FID" verbatim as a Titrations selection."""
    svc = _FakeAnalysisService({1: "GC-FID"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    assert sections[0].rows[-2].get_value(1) == "Analysis by GC-FID (average of triplicates)"


def test_can_build_sections_true_for_gc_fid():
    svc = _FakeAnalysisService({1: "GC-FID"})
    assert orchestrator.can_build_sections(_sample((1,)), svc) is True


def test_moisture_karl_fischer_dispatches_to_titrations_builder():
    """Confirmed real: the same real Chemical customer's intake form that
    confirmed "GC-FID" also uses "Moisture (Karl Fischer)" verbatim as a
    Titrations selection."""
    svc = _FakeAnalysisService({1: "Moisture (Karl Fischer)"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    assert sections[0].rows[-2].get_value(1) == "Analysis by KF-Titration"


def test_can_build_sections_true_for_moisture_karl_fischer():
    svc = _FakeAnalysisService({1: "Moisture (Karl Fischer)"})
    assert orchestrator.can_build_sections(_sample((1,)), svc) is True


# ---------------------------------------------------------------------------
# build_sections -- "5 Anions + MS Authentication" (confirmed real: one
# real Chemical customer's report)
# ---------------------------------------------------------------------------

def test_5_anions_plus_ms_authentication_renders_the_same_panel_as_plain_5_anions():
    svc = _FakeAnalysisService({1: "5 Anions + MS Authentication"})
    with_ms = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    svc2 = _FakeAnalysisService({1: "5 Anions"})
    plain = orchestrator.build_sections(_sample((1,)), svc2, _FakeElementService())
    with_ms_rows = [(r.get_value(2), r.get_value(3)) for r in with_ms[0].rows if r.style_name == "DataLabel"]
    plain_rows = [(r.get_value(2), r.get_value(3)) for r in plain[0].rows if r.style_name == "DataLabel"]
    assert with_ms_rows == plain_rows


# ---------------------------------------------------------------------------
# build_sections -- metals_prep_text (confirmed real: a real Chemical
# customer's report used "Evaporation"; real Water customers' reports use
# "Dilute and Shoot")
# ---------------------------------------------------------------------------

def test_metals_panel_uses_default_prep_text_when_not_given():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    footer = next(r for r in sections[0].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1)))
    assert footer.get_value(1) == "Analysis by ICPMS (Evaporation)"


def test_metals_panel_uses_caller_supplied_prep_text():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(
        _sample((1,)), svc, _FakeElementService(), metals_prep_text="Dilute and Shoot"
    )
    footer = next(r for r in sections[0].rows if r.get_value(1) and "Analysis by ICPMS" in str(r.get_value(1)))
    assert footer.get_value(1) == "Analysis by ICPMS (Dilute and Shoot)"


def test_metals_panel_uses_default_instrument_icpms_when_not_given():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert "ICPMS" in _footer_text(sections[0])


def test_metals_specs_thread_through_to_the_panel_column_1():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(
        _sample((1,)), svc, _FakeElementService(), metals_specs={"Al": 0.3}
    )
    al_row = next(r for r in sections[0].rows if r.get_value(3) == "Al")
    assert al_row.get_value(1) == 0.3


def test_metals_specs_default_none_leaves_column_1_blank():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    al_row = next(r for r in sections[0].rows if r.get_value(3) == "Al")
    assert al_row.get_value(1) is None


def test_metals_panel_uses_caller_supplied_instrument():
    """Confirmed real: a very dirty/nasty matrix, or one that itself
    contains a metal (e.g. NaOH), is manually switched to ICPOES during
    the quote process -- the stored value has no hyphen, but the real
    report text does ("ICP-OES")."""
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(
        _sample((1,)), svc, _FakeElementService(), metals_instrument="ICPOES"
    )
    assert _footer_text(sections[0]) == "Analysis by ICP-OES (Evaporation)"


def test_caller_supplied_instrument_applies_to_additional_elements_block_too():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(
        _sample((1,), additional_element_ids=(101, 102)), svc, _FakeElementService(), metals_instrument="ICPOES"
    )
    footers = [r.get_value(1) for r in sections[0].rows if r.get_value(1) and "Analysis by" in str(r.get_value(1))]
    assert footers == ["Analysis by ICP-OES (Evaporation)", "Analysis by ICP-OES (Evaporation)"]


# ---------------------------------------------------------------------------
# build_sections -- additional elements (confirmed real: several different
# real customers' reports -- previously silently dropped entirely)
# ---------------------------------------------------------------------------

def test_additional_elements_attach_to_existing_metals_panel_as_second_block():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(_sample((1,), additional_element_ids=(101, 102)), svc, _FakeElementService())
    assert len(sections) == 1  # still one section, not a separate one
    section = sections[0]
    label_row = next(r for r in section.rows if r.get_value(4) == "Additional Elements")
    idx = section.rows.index(label_row)
    sb_row, as_row = section.rows[idx + 1], section.rows[idx + 2]
    assert (sb_row.get_value(2), sb_row.get_value(3)) == ("Antimony", "Sb")
    assert (as_row.get_value(2), as_row.get_value(3)) == ("Arsenic", "As")
    # two independent footers: the main panel's, then the additional block's
    footers = [r.get_value(1) for r in section.rows if r.get_value(1) and "Analysis by" in str(r.get_value(1))]
    assert footers == ["Analysis by ICPMS (Evaporation)", "Analysis by ICPMS (Evaporation)"]


def test_additional_elements_alone_build_a_standalone_minimal_panel():
    """Confirmed real (a real Water customer's sample requesting only
    free-text elements): no catalog panel selected at all, just additional
    elements."""
    svc = _FakeAnalysisService({})
    sections = orchestrator.build_sections(
        _sample((), additional_element_ids=(101, 102)), svc, _FakeElementService(),
        metals_prep_text="Dilute and Shoot",
    )
    assert len(sections) == 1
    section = sections[0]
    assert not any(r.get_value(4) == "Additional Elements" for r in section.rows)  # no label -- standalone shape
    assert not any(r.get_value(2) and "AVERAGE" in str(r.get_value(2)) for r in section.rows)  # no summary
    assert _footer_text(section) == "Analysis by ICPMS (Dilute and Shoot)"


# ---------------------------------------------------------------------------
# build_sections -- additional_elements_prep_text override (customer-level
# flag, confirmed real: at least one customer's additional elements are
# run by a different method than their main panel)
# ---------------------------------------------------------------------------

def test_additional_elements_prep_override_applies_only_to_the_second_footer():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(
        _sample((1,), additional_element_ids=(101, 102)), svc, _FakeElementService(),
        metals_prep_text="Evaporation", additional_elements_prep_text="Alternate Method",
    )
    footers = [r.get_value(1) for r in sections[0].rows if r.get_value(1) and "Analysis by" in str(r.get_value(1))]
    assert footers == ["Analysis by ICPMS (Evaporation)", "Analysis by ICPMS (Alternate Method)"]


def test_additional_elements_prep_override_applies_to_standalone_panel_too():
    svc = _FakeAnalysisService({})
    sections = orchestrator.build_sections(
        _sample((), additional_element_ids=(101, 102)), svc, _FakeElementService(),
        metals_prep_text="Dilute and Shoot", additional_elements_prep_text="Alternate Method",
    )
    assert sections[0].rows[-2].get_value(1) == "Analysis by ICPMS (Alternate Method)"


def test_no_additional_elements_prep_override_falls_back_to_metals_prep_text():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(
        _sample((1,), additional_element_ids=(101, 102)), svc, _FakeElementService(),
        metals_prep_text="Evaporation",
    )
    footers = [r.get_value(1) for r in sections[0].rows if r.get_value(1) and "Analysis by" in str(r.get_value(1))]
    assert footers == ["Analysis by ICPMS (Evaporation)", "Analysis by ICPMS (Evaporation)"]


def test_no_additional_elements_no_change_in_section_count():
    svc = _FakeAnalysisService({1: "36 Elements"})
    sections = orchestrator.build_sections(_sample((1,)), svc, _FakeElementService())
    assert len(sections) == 1
    assert not any(r.get_value(4) == "Additional Elements" for r in sections[0].rows)


def test_can_build_sections_true_for_additional_elements_only():
    svc = _FakeAnalysisService({})
    assert orchestrator.can_build_sections(_sample((), additional_element_ids=(101,)), svc) is True
