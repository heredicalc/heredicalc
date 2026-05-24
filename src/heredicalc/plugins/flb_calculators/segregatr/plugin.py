"""segregatr FLB calculator plugin — subprocess wrapper for R/segregatr."""

from __future__ import annotations

import json
import subprocess
import tempfile
from importlib.resources import files as _files
from pathlib import Path
from typing import Any

from heredicalc.core.exceptions import SegregaError
from heredicalc.core.models.pedigree import Pedigree
from heredicalc.core.models.penetrance import PenetranceTable
from heredicalc.core.models.plugin import PluginMeta

_SCRIPT = _files(__package__) / "compute_flb.R"


class SegregatrFLBCalculator:
    """FLB calculator that calls the R ``segregatr`` package via subprocess.

    Writes a pedigree TSV and a penetrance TSV to temp files, executes
    ``Rscript --vanilla compute_flb.R``, and parses JSON stdout.
    Temp files are preserved on error and deleted on success.
    """

    meta = PluginMeta(
        name="segregatr",
        version="1.0.0",
        kind="flb_calculator",
        description="FLB calculator via R/segregatr subprocess",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "penetrance_model": ["victor"],
        },
    )

    def compute(
        self,
        pedigree: Pedigree,
        penetrance_output: Any,
        liability_map: dict[int, int],
        allele_freq: float,
        params: dict[str, Any],
    ) -> float:
        """Compute the FLB via R/segregatr.

        :param liability_map: ``individual_id`` → zero-based liability class index.
        :raises SegregaError: If Rscript returns a non-zero exit code.
        """
        table: PenetranceTable = penetrance_output
        ped_path: Path | None = None
        pen_path: Path | None = None

        try:
            ped_path = _write_pedigree_tsv(pedigree, liability_map)
            pen_path = _write_penetrance_tsv(table)

            script_path = str(_SCRIPT)
            cmd = [
                "Rscript",
                "--vanilla",
                script_path,
                str(ped_path),
                str(pen_path),
                str(allele_freq),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise SegregaError(
                    f"segregatr FLB computation failed (exit {result.returncode})",
                    returncode=result.returncode,
                    stderr=result.stderr,
                    temp_files=[str(ped_path), str(pen_path)],
                )

            stdout = result.stdout.strip()
            parsed = json.loads(stdout)
            flb = float(parsed["flb"])

            # Clean up temp files on success
            ped_path.unlink(missing_ok=True)
            pen_path.unlink(missing_ok=True)
            return flb

        except SegregaError:
            raise
        except Exception as exc:
            temp_files = [str(p) for p in [ped_path, pen_path] if p is not None]
            raise SegregaError(
                f"Unexpected error in segregatr FLB computation: {exc}",
                temp_files=temp_files,
            ) from exc


def _write_pedigree_tsv(pedigree: Pedigree, liability_map: dict[int, int]) -> Path:
    """Write pedigree members to a temp TSV for the R script."""
    fd, path_str = tempfile.mkstemp(suffix="_pedigree.tsv", prefix="heredicalc_")
    path = Path(path_str)
    lines = [
        "individual_id\tfather_id\tmother_id\tsex_code\tis_affected\tgenotype\tliability_class"
    ]
    for m in pedigree.members:
        sex_code = 1 if m.sex == "M" else (2 if m.sex == "F" else 1)
        is_affected = 1 if m.is_affected else 0
        genotype = m.genotype if m.genotype else "NA"
        father_id = m.father_id if m.father_id is not None else 0
        mother_id = m.mother_id if m.mother_id is not None else 0
        liability_class = liability_map[m.individual_id]
        lines.append(
            f"{m.individual_id}\t{father_id}\t{mother_id}\t{sex_code}\t"
            f"{is_affected}\t{genotype}\t{liability_class}"
        )
    import os

    os.close(fd)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_penetrance_tsv(table: PenetranceTable) -> Path:
    """Write the penetrance table to a temp TSV for the R script."""
    fd, path_str = tempfile.mkstemp(suffix="_penetrance.tsv", prefix="heredicalc_")
    path = Path(path_str)
    lines = ["penetrance_nc\tpenetrance_het\tpenetrance_hom"]
    for row in table.rows:
        lines.append(f"{row.penetrance_nc}\t{row.penetrance_het}\t{row.penetrance_hom}")
    import os

    os.close(fd)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
