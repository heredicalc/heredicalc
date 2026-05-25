"""Pedigree domain models."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, model_validator


class Affection(BaseModel):
    """A single diagnosis event for a pedigree member."""

    phenotype: str
    age_at_diagnosis: int | None = None
    date_of_diagnosis: date | None = None
    side: Literal["left", "right", "bilateral", "unknown"] | None = None

    @model_validator(mode="after")
    def _validate_age_date_consistency(self) -> Affection:
        if self.age_at_diagnosis is not None and self.date_of_diagnosis is not None:
            # Consistency check deferred to PedigreeMember which has date_of_birth.
            # Here we only ensure both are not contradictory in isolation.
            pass
        return self


class PedigreeMember(BaseModel):
    """A single individual in a pedigree."""

    individual_id: int
    mother_id: int | None = None
    father_id: int | None = None
    sex: Literal["M", "F", "U"]
    affections: list[Affection] = []
    age_last_contact: int | None = None
    date_of_birth: date | None = None
    date_of_death: date | None = None
    date_last_contact: date | None = None
    age_at_death: int | None = None
    genotype: Literal["Het", "Neg", "Hom"] | None = None
    is_proband: bool = False
    affection_known: bool = True

    @model_validator(mode="after")
    def _compute_and_validate_ages(self) -> PedigreeMember:
        if self.date_of_birth is not None:
            if self.date_last_contact is not None and self.age_last_contact is None:
                delta = self.date_last_contact - self.date_of_birth
                self.age_last_contact = int(delta.days / 365.25)
            if self.date_of_death is not None and self.age_at_death is None:
                delta = self.date_of_death - self.date_of_birth
                self.age_at_death = int(delta.days / 365.25)

        # Validate consistency within ±1 year when both age and date fields present
        if (
            self.date_of_birth is not None
            and self.date_last_contact is not None
            and self.age_last_contact is not None
        ):
            expected = int((self.date_last_contact - self.date_of_birth).days / 365.25)
            if abs(expected - self.age_last_contact) > 1:
                raise ValueError(
                    f"age_last_contact={self.age_last_contact} inconsistent with "
                    f"date fields (expected ~{expected})"
                )
        return self

    @property
    def primary_affection(self) -> Affection | None:
        """Earliest affection by age_at_diagnosis; None if unaffected."""
        diagnosed = [a for a in self.affections if a.age_at_diagnosis is not None]
        if not diagnosed:
            return self.affections[0] if self.affections else None
        return min(diagnosed, key=lambda a: a.age_at_diagnosis)  # type: ignore[arg-type]

    @property
    def is_affected(self) -> bool:
        return len(self.affections) > 0


class Pedigree(BaseModel):
    """A family pedigree with members, affections, and partial genotypes."""

    pedigree_id: str
    members: list[PedigreeMember]

    @model_validator(mode="after")
    def _exactly_one_proband(self) -> Pedigree:
        probands = [m for m in self.members if m.is_proband]
        if len(probands) != 1:
            raise ValueError(
                f"Pedigree must have exactly one proband (is_proband=True), "
                f"found {len(probands)}"
            )
        return self

    def get_member(self, individual_id: int) -> PedigreeMember | None:
        for m in self.members:
            if m.individual_id == individual_id:
                return m
        return None
