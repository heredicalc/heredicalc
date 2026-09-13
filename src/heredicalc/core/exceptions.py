"""Domain exceptions for HerediCalc core."""

from __future__ import annotations


class HerediCalcError(Exception):
    """Base class for all HerediCalc exceptions."""


class PluginResolutionError(HerediCalcError):
    """Raised when a plugin cannot be resolved from the registry."""

    def __init__(
        self,
        kind: str,
        constraint: str = "",
        available: list[str] | None = None,
        reason: str = "",
    ) -> None:
        self.kind = kind
        self.constraint = constraint
        self.available = available or []
        self.reason = reason
        msg = f"Cannot resolve plugin kind={kind!r} constraint={constraint!r}"
        if reason:
            msg += f": {reason}"
        if self.available:
            msg += f". Available: {self.available}"
        super().__init__(msg)


class PluginCompatibilityError(HerediCalcError):
    """Raised when two plugins declare incompatible requirements."""


class CircularDependencyError(HerediCalcError):
    """Raised when a circular plugin dependency is detected."""


class UnknownPluginKindError(HerediCalcError):
    """Raised when a plugin is registered for an unknown kind."""


class DataSchemaError(HerediCalcError):
    """Raised when a DataFrame does not conform to the expected schema."""


class DataIntegrityError(HerediCalcError):
    """Raised when data files fail an integrity assertion."""


class SegregaError(HerediCalcError):
    """Raised when the segregatr R subprocess fails."""

    def __init__(
        self,
        message: str,
        returncode: int = -1,
        stderr: str = "",
        temp_files: list[str] | None = None,
    ) -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.temp_files = temp_files or []
        super().__init__(message)


class ZeroPenetranceError(HerediCalcError):
    """Raised when an affected member's liability class carries no penetrance data."""

    def __init__(
        self,
        individual_id: int,
        group: dict[str, str],
        reason: str = "",
        pedigree_id: str | None = None,
    ) -> None:
        self.individual_id = individual_id
        self.group = dict(group)
        self.reason = reason
        self.pedigree_id = pedigree_id
        where = f"member {individual_id}"
        if pedigree_id is not None:
            where += f" of pedigree {pedigree_id!r}"
        fields = ", ".join(f"{k}={v!r}" for k, v in self.group.items())
        msg = f"Affected {where} has no penetrance data for liability class {fields}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class UnknownAgeError(HerediCalcError):
    """Raised when an unaffected member has no age and no policy says how to treat that."""

    PARAM = "unaffected_unknown_age"

    def __init__(
        self,
        individual_id: int,
        reason: str = "",
        pedigree_id: str | None = None,
    ) -> None:
        self.individual_id = individual_id
        self.reason = reason
        self.pedigree_id = pedigree_id
        where = f"member {individual_id}"
        if pedigree_id is not None:
            where += f" of pedigree {pedigree_id!r}"
        msg = (
            f"Unaffected {where} has no age_last_contact and params[{self.PARAM!r}] is not "
            "set; set it to 'uninformative' or to a fixed age (e.g. 99)"
        )
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
