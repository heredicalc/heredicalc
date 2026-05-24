"""Unit tests for the plugin registry."""

from __future__ import annotations

import pytest

from heredicalc.core.exceptions import (
    CircularDependencyError,
    PluginCompatibilityError,
    PluginResolutionError,
    UnknownPluginKindError,
)
from heredicalc.core.models.plugin import PluginMeta
from heredicalc.core.models.pedigree import Pedigree, PedigreeMember
from heredicalc.core.registry.registry import PluginRegistry


def _meta(**kwargs) -> PluginMeta:
    defaults = dict(
        name="test",
        version="1.0.0",
        kind="pedigree_format",
        description="test",
        author="test",
        min_api_version="1.0.0",
        max_api_version=None,
        requires={},
        compatible_with={},
    )
    defaults.update(kwargs)
    return PluginMeta(**defaults)


class FakePlugin:
    meta = _meta(name="fake", version="1.0.0", kind="pedigree_format")

    def __init__(self, **kwargs):
        pass


class FakePluginV2:
    meta = _meta(name="fake", version="2.0.0", kind="pedigree_format")

    def __init__(self, **kwargs):
        pass


class ApiTooNew:
    meta = _meta(name="too_new", kind="pedigree_format", min_api_version="99.0.0")

    def __init__(self, **kwargs):
        pass


class ApiExpired:
    meta = _meta(
        name="expired",
        kind="pedigree_format",
        min_api_version="1.0.0",
        max_api_version="0.9.0",
    )

    def __init__(self, **kwargs):
        pass


class DepA:
    meta = _meta(name="dep_a", kind="rr_model")

    def __init__(self, **kwargs):
        pass


class DepB:
    meta = _meta(name="dep_b", kind="crhf_model", requires={"rr_model": "dep_a"})

    def __init__(self, rr_model, **kwargs):
        self.rr_model = rr_model


class CircularA:
    meta = _meta(name="circ_a", kind="rr_model", requires={"crhf_model": "circ_b"})

    def __init__(self, **kwargs):
        pass


class CircularB:
    meta = _meta(name="circ_b", kind="crhf_model", requires={"rr_model": "circ_a"})

    def __init__(self, **kwargs):
        pass


class CompatPen:
    meta = _meta(
        name="compat_pen",
        kind="penetrance_model",
        compatible_with={"flb_calculator": ["segregatr"]},
    )

    def __init__(self, **kwargs):
        pass


class Segregatr:
    meta = _meta(name="segregatr", kind="flb_calculator")

    def __init__(self, **kwargs):
        pass


class OtherCalc:
    meta = _meta(name="other_calc", kind="flb_calculator")

    def __init__(self, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Kind registration
# ---------------------------------------------------------------------------


class TestKindRegistration:
    def test_ten_builtin_kinds(self):
        reg = PluginRegistry()
        assert len(reg.known_kinds()) == 10

    def test_builtin_kinds_present(self):
        reg = PluginRegistry()
        kinds = reg.known_kinds()
        for k in (
            "pedigree_format",
            "phenotype_model",
            "incidence_source",
            "trait_mapper",
            "hazard_model",
            "penetrance_model",
            "crhf_model",
            "rr_model",
            "liability_assigner",
            "flb_calculator",
        ):
            assert k in kinds

    def test_register_new_kind(self):
        reg = PluginRegistry()
        reg.register_kind("my_custom_kind")
        assert "my_custom_kind" in reg.known_kinds()

    def test_register_kind_idempotent(self):
        reg = PluginRegistry()
        reg.register_kind("dup_kind")
        reg.register_kind("dup_kind")
        assert reg.known_kinds().count("dup_kind") == 1

    def test_register_plugin_unknown_kind_raises(self):
        reg = PluginRegistry()

        class Ghost:
            meta = _meta(name="ghost", kind="nonexistent_kind")

        with pytest.raises(UnknownPluginKindError):
            reg.register(Ghost)


# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------


class TestVersionResolution:
    def test_resolve_latest_when_multiple_versions(self):
        reg = PluginRegistry()
        reg.register(FakePlugin)
        reg.register(FakePluginV2)
        entry = reg.resolve("pedigree_format", "fake")
        assert entry.meta.version == "2.0.0"

    def test_resolve_with_upper_bound(self):
        reg = PluginRegistry()
        reg.register(FakePlugin)
        reg.register(FakePluginV2)
        entry = reg.resolve("pedigree_format", "fake<2.0.0")
        assert entry.meta.version == "1.0.0"

    def test_resolve_exact_version(self):
        reg = PluginRegistry()
        reg.register(FakePlugin)
        reg.register(FakePluginV2)
        entry = reg.resolve("pedigree_format", "fake==1.0.0")
        assert entry.meta.version == "1.0.0"

    def test_resolve_missing_name_raises(self):
        reg = PluginRegistry()
        with pytest.raises(PluginResolutionError) as exc:
            reg.resolve("pedigree_format", "does_not_exist")
        assert exc.value.kind == "pedigree_format"
        assert "name not found" in exc.value.reason

    def test_resolve_unsatisfiable_version_raises(self):
        reg = PluginRegistry()
        reg.register(FakePlugin)
        with pytest.raises(PluginResolutionError) as exc:
            reg.resolve("pedigree_format", "fake>=9.0.0")
        assert "no compatible version" in exc.value.reason

    def test_resolve_unknown_kind_raises(self):
        reg = PluginRegistry()
        with pytest.raises(UnknownPluginKindError):
            reg.resolve("completely_unknown_kind", "fake")


# ---------------------------------------------------------------------------
# API version filtering
# ---------------------------------------------------------------------------


class TestApiVersionFiltering:
    def test_min_api_too_new_filtered_out(self):
        reg = PluginRegistry()
        reg.register(ApiTooNew)
        with pytest.raises(PluginResolutionError):
            reg.resolve("pedigree_format", "too_new")

    def test_max_api_exceeded_filtered_out(self):
        reg = PluginRegistry()
        reg.register(ApiExpired)
        with pytest.raises(PluginResolutionError):
            reg.resolve("pedigree_format", "expired")

    def test_compatible_api_version_resolves(self):
        reg = PluginRegistry()
        reg.register(FakePlugin)
        entry = reg.resolve("pedigree_format", "fake")
        assert entry.meta.name == "fake"


# ---------------------------------------------------------------------------
# Compatibility validation
# ---------------------------------------------------------------------------


class TestCompatibilityValidation:
    def test_compatible_pair_passes(self):
        reg = PluginRegistry()
        pen = CompatPen()
        calc = Segregatr()
        reg.validate_compatibility({"penetrance_model": pen, "flb_calculator": calc})

    def test_incompatible_pair_raises(self):
        reg = PluginRegistry()
        pen = CompatPen()
        calc = OtherCalc()
        with pytest.raises(PluginCompatibilityError):
            reg.validate_compatibility({"penetrance_model": pen, "flb_calculator": calc})

    def test_missing_compatible_kind_ignored(self):
        reg = PluginRegistry()
        pen = CompatPen()
        # No flb_calculator in the dict → no error (kind absent means can't check)
        reg.validate_compatibility({"penetrance_model": pen})


# ---------------------------------------------------------------------------
# Circular dependency detection
# ---------------------------------------------------------------------------


class TestCircularDependencyDetection:
    def test_circular_deps_detected(self):
        reg = PluginRegistry()
        reg.register(CircularA)
        reg.register(CircularB)
        with pytest.raises(CircularDependencyError):
            reg._run_circular_dep_check()

    def test_linear_deps_ok(self):
        reg = PluginRegistry()
        reg.register(DepA)
        reg.register(DepB)
        reg._run_circular_dep_check()


# ---------------------------------------------------------------------------
# Pedigree domain validators
# ---------------------------------------------------------------------------


class TestPedigreeValidators:
    def test_no_proband_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Pedigree(
                pedigree_id="t",
                members=[
                    PedigreeMember(individual_id=1, sex="M"),
                    PedigreeMember(individual_id=2, sex="F"),
                ],
            )

    def test_two_probands_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Pedigree(
                pedigree_id="t",
                members=[
                    PedigreeMember(individual_id=1, sex="M", is_proband=True),
                    PedigreeMember(individual_id=2, sex="F", is_proband=True),
                ],
            )

    def test_exactly_one_proband_ok(self):
        p = Pedigree(
            pedigree_id="t",
            members=[
                PedigreeMember(individual_id=1, sex="M", is_proband=True),
                PedigreeMember(individual_id=2, sex="F"),
            ],
        )
        assert p.pedigree_id == "t"
