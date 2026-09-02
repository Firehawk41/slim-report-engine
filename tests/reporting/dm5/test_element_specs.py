from slim_report_engine.reporting.dm5 import element_specs


def test_nh4oh_specs_omits_elements_with_no_spec():
    """Reproduced verbatim: Beryllium/Bismuth/Gallium etc. have no spec on
    the real NH4OH sheet, so they're simply absent, not zero."""
    specs = element_specs.nh4oh_specs()
    assert "Be" not in specs
    assert "Bi" not in specs
    assert "Ga" not in specs
    assert specs["Al"] == 0.1


def test_dm5n_and_dm5s_hf49_specs_genuinely_differ():
    n = element_specs.hf49_specs()
    s = element_specs.hf49_specs_s()
    assert n["Ca"] == 0.5
    assert s["Ca"] == 0.08
    assert n != s


def test_surf_etch_is_dm5s_only_with_higher_thresholds():
    specs = element_specs.surf_etch_specs()
    assert specs["Na"] == 200
    assert "Al" not in specs  # unlike the acid/base chemicals


def test_hf_composite_specs_shared_across_all_three_composite_sheets():
    element = element_specs.hf_composite_element_specs()
    anion = element_specs.hf_composite_anion_specs()
    assert element["Al"] == 0.08
    assert anion == {"Cl": 40, "NO3": 60, "SO4": 30, "PO4": 10}
