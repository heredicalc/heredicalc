"""HerediCalc v4 command-line interface."""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from heredicalc.core.app_dirs import user_traits_dir
from heredicalc.core.exceptions import HerediCalcError, SegregaError
from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry
from heredicalc.core.trait_manifest import VALID_KINDS, get_entry, load_manifest, remove_entry, upsert_entry

app = typer.Typer(
    name="heredicalc",
    help="HerediCalc v4 — FLB factor for hereditary cosegregation analysis.",
    add_completion=False,
)
console = Console()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_registry() -> PluginRegistry:
    reg = PluginRegistry()
    reg.discover_all()
    return reg


def _load_config(config_path: Path | None, overrides: dict[str, Any]) -> PipelineConfig:
    data: dict[str, Any] = {}
    if config_path is not None:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    computation = data.get("computation", {})
    plugins = data.get("plugins", {})

    for key, val in overrides.items():
        if val is not None:
            if key in ("genetic_entity", "allele_freq"):
                computation[key] = val
            elif key in (
                "incidence_source",
                "phenotype_model",
                "trait_mapper",
                "hazard_model",
                "penetrance_model",
                "liability_assigner",
                "flb_calculator",
                "pedigree_format",
            ):
                plugins[key] = val
            else:
                plugins.setdefault("params", {})[key] = val

    return PipelineConfig(
        computation=ComputationConfig(**computation),
        plugins=PluginConfig(**plugins),
    )


def _bundled_crhf(name: str) -> float | None:
    """Return CRHF value from bundled genes.csv, or None if not present."""
    from importlib.resources import files as _files
    import pandas as pd
    _DATA = _files("heredicalc.plugins.crhf_models.lookup") / "data"
    csv_path = Path(str(_DATA / "genes.csv"))
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    row = df[df["gene"] == name]
    if row.empty:
        return None
    return float(row.iloc[0]["crhf_value"])


def _bundled_rr_path(name: str) -> Path | None:
    """Return path to bundled RR CSV for *name*, or None."""
    from importlib.resources import files as _files
    _DATA = _files("heredicalc.plugins.rr_models.tabular") / "data"
    p = Path(str(_DATA / f"{name}.csv"))
    return p if p.exists() and p.stat().st_size > 0 else None


def _user_rr_path(name: str) -> Path:
    return user_traits_dir() / "rr" / f"{name}.csv"


def _is_user_trait(name: str) -> bool:
    """True if the trait has any user-local data (manifest entry or RR file)."""
    return get_entry(name) is not None or _user_rr_path(name).exists()


def _generate_template(name: str) -> str:
    """Generate a placeholder RR CSV with all standard bands set to 1.0."""
    rows = [
        ("gene", "gender", "age_from", "age_to", "phenotype", "heterozygous_rr", "homozygous_rr"),
        # Female breast cancer bands
        (name, "F", 0, 29, "BreastCancer", 1.0, 1.0),
        (name, "F", 30, 39, "BreastCancer", 1.0, 1.0),
        (name, "F", 40, 49, "BreastCancer", 1.0, 1.0),
        (name, "F", 50, 59, "BreastCancer", 1.0, 1.0),
        (name, "F", 60, 69, "BreastCancer", 1.0, 1.0),
        (name, "F", 70, 79, "BreastCancer", 1.0, 1.0),
        (name, "F", 80, "", "BreastCancer", 1.0, 1.0),
        # Male breast cancer bands
        (name, "M", 0, 79, "BreastCancer", 1.0, 1.0),
        (name, "M", 80, "", "BreastCancer", 1.0, 1.0),
        # Ovarian cancer (female only)
        (name, "F", 0, 29, "OvarianCancer", 1.0, 1.0),
        (name, "F", 30, 39, "OvarianCancer", 1.0, 1.0),
        (name, "F", 40, 49, "OvarianCancer", 1.0, 1.0),
        (name, "F", 50, 59, "OvarianCancer", 1.0, 1.0),
        (name, "F", 60, 69, "OvarianCancer", 1.0, 1.0),
        (name, "F", 70, 79, "OvarianCancer", 1.0, 1.0),
        (name, "F", 80, "", "OvarianCancer", 1.0, 1.0),
        (name, "M", 0, "", "OvarianCancer", 1.0, 1.0),
        # Pancreatic cancer (both sexes)
        (name, "F", 0, 49, "PancreaticCancer", 1.0, 1.0),
        (name, "F", 50, 79, "PancreaticCancer", 1.0, 1.0),
        (name, "F", 80, "", "PancreaticCancer", 1.0, 1.0),
        (name, "M", 0, 49, "PancreaticCancer", 1.0, 1.0),
        (name, "M", 50, 79, "PancreaticCancer", 1.0, 1.0),
        (name, "M", 80, "", "PancreaticCancer", 1.0, 1.0),
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows(rows)
    return buf.getvalue()


def _parse_meta_pairs(meta_list: list[str]) -> dict[str, str]:
    """Parse ['key=value', ...] into a dict. Raises UsageError on bad format."""
    result: dict[str, str] = {}
    for item in meta_list:
        if "=" not in item:
            raise typer.BadParameter(f"Metadata must be key=value, got: {item!r}")
        k, _, v = item.partition("=")
        result[k.strip()] = v.strip()
    return result


def _prompt_meta_pairs(existing: dict[str, str]) -> dict[str, str]:
    """Interactively collect free-form key=value metadata pairs."""
    result = dict(existing)
    if result:
        console.print("Current metadata:")
        for k, v in result.items():
            console.print(f"  {k} = {v}")
    console.print("[dim]Enter metadata as key=value pairs (empty line to finish):[/dim]")
    while True:
        raw = typer.prompt("  key=value", default="", show_default=False)
        if not raw.strip():
            break
        if "=" not in raw:
            console.print("[yellow]  Format: key=value — try again[/yellow]")
            continue
        k, _, v = raw.partition("=")
        result[k.strip()] = v.strip()
    return result


def _write_rr_file(name: str, rr_file: Path) -> None:
    """Validate and copy *rr_file* into the user traits RR directory."""
    import pandas as pd
    df = pd.read_csv(rr_file)
    required = {"gene", "gender", "age_from", "phenotype", "heterozygous_rr", "homozygous_rr"}
    missing = required - set(df.columns)
    if missing:
        raise typer.BadParameter(f"RR file missing columns: {', '.join(sorted(missing))}")
    dest = _user_rr_path(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(rr_file.read_bytes())


def _run_clone_wizard(source: str, target: str, crhf_override: float | None) -> None:
    """Core clone logic shared by clone command and edit's built-in guard."""
    # Resolve source RR CSV
    src_user = _user_rr_path(source)
    if src_user.exists() and src_user.stat().st_size > 0:
        src_csv = src_user
    else:
        src_csv = _bundled_rr_path(source)
        if src_csv is None:
            raise typer.BadParameter(f"Source trait {source!r} has no RR data.")

    # Copy RR, replacing gene column
    import pandas as pd
    df = pd.read_csv(src_csv)
    df["gene"] = target
    dest = _user_rr_path(target)
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)

    # Resolve CRHF
    src_entry = get_entry(source)
    if crhf_override is not None:
        crhf = crhf_override
    elif src_entry is not None:
        crhf = src_entry["crhf_value"]
    else:
        bundled = _bundled_crhf(source)
        if bundled is None:
            raise typer.BadParameter(
                f"Source trait {source!r} has no CRHF value. Provide --crhf."
            )
        crhf = bundled

    # Build manifest entry (inherit kind + metadata from source)
    kind = src_entry["kind"] if src_entry else "gene"
    metadata = dict(src_entry.get("metadata", {})) if src_entry else {}

    upsert_entry({"name": target, "crhf_value": crhf, "kind": kind, "metadata": metadata})
    console.print(f"[green]✓[/green] Cloned {source!r} → {target!r} (CRHF={crhf})")
    console.print(f"  RR table: {dest}")
    console.print(f"  Run [bold]heredicalc edit trait {target}[/bold] to adjust values.")


# ---------------------------------------------------------------------------
# Core commands: run, batch
# ---------------------------------------------------------------------------

@app.command()
def run(
    pedigree: Annotated[Path, typer.Argument(help="Path to the pedigree file.")],
    config: Annotated[
        Optional[Path], typer.Option("--config", "-c", help="YAML config file.")
    ] = None,
    genetic_entity: Annotated[Optional[str], typer.Option(help="Genetic entity (e.g. BRCA1).")] = None,
    allele_freq: Annotated[Optional[float], typer.Option(help="Allele frequency.")] = None,
    population: Annotated[Optional[str], typer.Option(help="Population name or registry ID.")] = None,
    incidence_source: Annotated[Optional[str], typer.Option(help="Incidence source plugin.")] = None,
    phenotype_model: Annotated[Optional[str], typer.Option(help="Phenotype model plugin.")] = None,
    trait_mapper: Annotated[Optional[str], typer.Option(help="Trait mapper plugin.")] = None,
    penetrance_model: Annotated[Optional[str], typer.Option(help="Penetrance model plugin.")] = None,
    hazard_model: Annotated[Optional[str], typer.Option(help="Hazard model plugin.")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json, text.")] = "text",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Compute the FLB factor for a single pedigree."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    overrides = dict(
        genetic_entity=genetic_entity,
        allele_freq=allele_freq,
        population=population,
        incidence_source=incidence_source,
        phenotype_model=phenotype_model,
        trait_mapper=trait_mapper,
        penetrance_model=penetrance_model,
        hazard_model=hazard_model,
    )

    try:
        pipeline_config = _load_config(config, overrides)
        registry = _build_registry()
        runner = PipelineRunner(registry=registry)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(f"Computing FLB for {pedigree.name}...", total=None)
            flb = runner.run(pedigree, pipeline_config)

        if output_format == "json":
            typer.echo(json.dumps({"pedigree": str(pedigree), "flb": flb}))
        else:
            console.print(f"[bold green]FLB = {flb:.4f}[/bold green]  ({pedigree.name})")

    except (HerediCalcError, FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def batch(
    directory: Annotated[Path, typer.Argument(help="Directory containing pedigree files.")],
    config: Annotated[Optional[Path], typer.Option("--config", "-c")] = None,
    pattern: Annotated[str, typer.Option(help="File glob pattern.")] = "*.ped",
    workers: Annotated[int, typer.Option("--workers", "-j", help="Parallel workers.")] = 4,
    output_format: Annotated[str, typer.Option("--format")] = "json",
) -> None:
    """Compute FLB for all pedigrees in a directory (parallel)."""
    ped_files = sorted(directory.glob(pattern))
    if not ped_files:
        console.print(f"[yellow]No files matching {pattern!r} in {directory}[/yellow]")
        raise typer.Exit(code=0)

    pipeline_config = _load_config(config, {})
    registry = _build_registry()
    runner = PipelineRunner(registry=registry)

    results = []

    def _run_one(path: Path) -> tuple[str, float | None, str | None]:
        try:
            flb = runner.run(path, pipeline_config)
            return (path.name, flb, None)
        except Exception as exc:  # noqa: BLE001
            return (path.name, None, str(exc))

    with Progress(console=console) as progress:
        task = progress.add_task(f"Processing {len(ped_files)} pedigrees...", total=len(ped_files))
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_one, p): p for p in ped_files}
            for future in as_completed(futures):
                name, flb, err = future.result()
                results.append({"pedigree": name, "flb": flb, "error": err})
                progress.advance(task)

    if output_format == "json":
        typer.echo(json.dumps(results, indent=2))
    else:
        table = Table("Pedigree", "FLB", "Error")
        for r in sorted(results, key=lambda x: x["pedigree"]):
            flb_str = f"{r['flb']:.4f}" if r["flb"] is not None else "—"
            table.add_row(r["pedigree"], flb_str, r["error"] or "")
        console.print(table)


# ---------------------------------------------------------------------------
# `add` command group
# ---------------------------------------------------------------------------

add_app = typer.Typer(help="Add configuration files or new traits.")
app.add_typer(add_app, name="add")


def _add_config_wizard(output: Path | None) -> None:
    """Shared logic for the config wizard (used by `add config` and deprecated `init`)."""
    console.print("[bold]HerediCalc configuration generator[/bold]")
    registry = _build_registry()

    genetic_entity = typer.prompt("Genetic entity (e.g. BRCA1)")
    allele_freq = typer.prompt("Allele frequency", default="0.0001")

    incidence_options = [e.meta.name for e in registry.list_plugins("incidence_source")]
    console.print(f"Available incidence sources: {', '.join(incidence_options)}")
    incidence_source = typer.prompt("Incidence source", default="ci5_ix")

    population = typer.prompt("Population (name or registry ID)", default="Latvia")
    age_bands = typer.prompt("Age bands (comma-separated)", default="30,40,50,60,65,70,80")

    config = {
        "computation": {"genetic_entity": genetic_entity, "allele_freq": float(allele_freq)},
        "plugins": {
            "incidence_source": incidence_source,
            "phenotype_model": "hbopc",
            "trait_mapper": f"{incidence_source}_hbopc",
            "penetrance_model": "victor",
            "params": {
                "population": population,
                "age_bands": [int(b.strip()) for b in age_bands.split(",")],
            },
        },
    }

    default_name = str(output) if output is not None else "heredicalc.yml"
    dest_str = typer.prompt(
        "Output file (leave empty to print to stdout)",
        default=default_name,
    )

    yaml_text = yaml.dump(config, default_flow_style=False, sort_keys=False)

    if not dest_str.strip():
        typer.echo(yaml_text)
        return

    dest = Path(dest_str)
    if dest.exists():
        if not typer.confirm(f"{dest} already exists. Overwrite?", default=False):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(code=0)
    dest.write_text(yaml_text, encoding="utf-8")
    console.print(f"[green]Config written to {dest}[/green]")


@add_app.command("config")
def add_config(
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output path (default: asked interactively)."),
    ] = None,
) -> None:
    """Interactively generate a heredicalc.yml configuration file."""
    _add_config_wizard(output)


@add_app.command("trait")
def add_trait(
    name: Annotated[Optional[str], typer.Argument(help="Trait name (e.g. BRCA2).")] = None,
    crhf: Annotated[Optional[float], typer.Option(help="CRHF value (allele frequency).")] = None,
    kind: Annotated[Optional[str], typer.Option(help=f"Trait kind: {', '.join(sorted(VALID_KINDS))}.")] = None,
    rr_file: Annotated[Optional[Path], typer.Option(help="RR CSV file to import.")] = None,
    meta: Annotated[Optional[list[str]], typer.Option(help="Metadata as key=value (repeatable).")] = None,
) -> None:
    """Add a new user-defined trait (RR table + CRHF value)."""
    if name is None:
        name = typer.prompt("Trait name (e.g. BRCA2)")

    # kind
    kind_options = sorted(VALID_KINDS)
    if kind is None:
        console.print(f"[dim]Trait kinds: {', '.join(kind_options)}[/dim]")
        kind = typer.prompt("Kind", default="gene")
    if kind not in VALID_KINDS:
        console.print(f"[yellow]Unknown kind {kind!r}. Valid: {', '.join(kind_options)}[/yellow]")
        raise typer.Exit(code=1)

    # CRHF
    bundled_q = _bundled_crhf(name)
    if crhf is None:
        default_q = str(bundled_q) if bundled_q is not None else "0.0001"
        if bundled_q is not None:
            console.print(f"[dim]Bundled CRHF for {name}: {bundled_q}[/dim]")
        crhf = float(typer.prompt("CRHF value (allele frequency)", default=default_q))

    # Metadata
    existing_meta: dict[str, str] = {}
    if meta:
        existing_meta = _parse_meta_pairs(meta)
    else:
        existing_meta = _prompt_meta_pairs({})

    # RR data
    if rr_file is not None:
        _write_rr_file(name, rr_file)
        console.print(f"[green]✓[/green] RR table imported from {rr_file}")
    else:
        template_csv = _generate_template(name)
        tmpl_path = user_traits_dir() / "rr" / f"{name}_template.csv"
        tmpl_path.parent.mkdir(parents=True, exist_ok=True)
        tmpl_path.write_text(template_csv, encoding="utf-8")
        console.print(f"\n[yellow]No --rr-file provided.[/yellow] A template has been written to:")
        console.print(f"  {tmpl_path}")
        console.print(
            "\nFill in the RR values, then re-run:\n"
            f"  [bold]heredicalc add trait {name} --rr-file {tmpl_path}[/bold]\n"
        )
        # Save manifest entry without RR file (CRHF + kind + metadata still usable)
        upsert_entry({"name": name, "crhf_value": crhf, "kind": kind, "metadata": existing_meta})
        console.print(f"[green]✓[/green] Trait {name!r} saved to manifest (RR table pending).")
        return

    upsert_entry({"name": name, "crhf_value": crhf, "kind": kind, "metadata": existing_meta})
    console.print(f"[green]✓[/green] Trait {name!r} added (CRHF={crhf}, kind={kind}).")


# ---------------------------------------------------------------------------
# `edit` command group
# ---------------------------------------------------------------------------

edit_app = typer.Typer(help="Edit user-defined traits.")
app.add_typer(edit_app, name="edit")


@edit_app.command("trait")
def edit_trait(
    name: Annotated[str, typer.Argument(help="Trait name to edit.")],
    rr_file: Annotated[Optional[Path], typer.Option(help="Replace RR table from this file.")] = None,
    meta: Annotated[Optional[list[str]], typer.Option(help="Replace metadata key=value (repeatable).")] = None,
) -> None:
    """Edit a user-defined trait (CRHF, kind, metadata, RR table)."""
    # Built-in guard: if no user data exists, offer to clone first
    if not _is_user_trait(name):
        bundled_rr = _bundled_rr_path(name)
        bundled_q = _bundled_crhf(name)
        if bundled_rr is None and bundled_q is None:
            console.print(f"[red]Trait {name!r} not found.[/red]")
            raise typer.Exit(code=1)
        console.print(
            f"[yellow]{name!r} is a built-in trait (read-only).[/yellow]\n"
            "Clone it to your user directory first to edit it."
        )
        if typer.confirm(f"Clone {name!r} to user directory now?", default=False):
            crhf_arg = float(typer.prompt("CRHF value", default=str(bundled_q or 0.0001)))
            _run_clone_wizard(name, name, crhf_arg)
        else:
            raise typer.Exit(code=0)

    entry = get_entry(name) or {"name": name, "crhf_value": 0.0001, "kind": "gene", "metadata": {}}

    # CRHF
    new_crhf = float(typer.prompt("CRHF value", default=str(entry["crhf_value"])))

    # kind
    console.print(f"[dim]Trait kinds: {', '.join(sorted(VALID_KINDS))}[/dim]")
    new_kind = typer.prompt("Kind", default=entry.get("kind", "gene"))
    if new_kind not in VALID_KINDS:
        console.print(f"[yellow]Unknown kind {new_kind!r} — keeping {entry.get('kind', 'gene')!r}[/yellow]")
        new_kind = entry.get("kind", "gene")

    # Metadata
    if meta:
        new_meta = _parse_meta_pairs(meta)
    else:
        new_meta = _prompt_meta_pairs(entry.get("metadata", {}))

    # RR file
    if rr_file is not None:
        _write_rr_file(name, rr_file)
        console.print(f"[green]✓[/green] RR table replaced from {rr_file}")
    else:
        rr_path = _user_rr_path(name)
        if rr_path.exists():
            editor = os.environ.get("EDITOR", "")
            if editor and typer.confirm(f"Open RR table in {editor}?", default=False):
                os.system(f"{editor} {rr_path}")  # noqa: S605

    upsert_entry({"name": name, "crhf_value": new_crhf, "kind": new_kind, "metadata": new_meta})
    console.print(f"[green]✓[/green] Trait {name!r} updated.")


# ---------------------------------------------------------------------------
# `clone` command group
# ---------------------------------------------------------------------------

clone_app = typer.Typer(help="Clone a trait as basis for a new one.")
app.add_typer(clone_app, name="clone")


@clone_app.command("trait")
def clone_trait(
    source: Annotated[str, typer.Argument(help="Source trait name (built-in or user).")],
    target: Annotated[str, typer.Argument(help="New trait name.")],
    crhf: Annotated[Optional[float], typer.Option(help="Override CRHF value for the new trait.")] = None,
) -> None:
    """Clone an existing trait (built-in or user) as basis for a new one."""
    if get_entry(target) is not None or _user_rr_path(target).exists():
        if not typer.confirm(f"Trait {target!r} already exists. Overwrite?", default=False):
            raise typer.Exit(code=0)
    _run_clone_wizard(source, target, crhf)


# ---------------------------------------------------------------------------
# `remove` command group
# ---------------------------------------------------------------------------

remove_app = typer.Typer(help="Remove user-defined traits.")
app.add_typer(remove_app, name="remove")


@remove_app.command("trait")
def remove_trait(
    name: Annotated[str, typer.Argument(help="Trait name to remove.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Remove a user-defined trait (RR table + manifest entry)."""
    rr_path = _user_rr_path(name)
    entry = get_entry(name)

    if entry is None and not rr_path.exists():
        bundled = _bundled_crhf(name) is not None or _bundled_rr_path(name) is not None
        if bundled:
            console.print(
                f"[yellow]{name!r} is a built-in trait — nothing to remove.[/yellow]\n"
                "Built-in traits cannot be deleted. Use [bold]heredicalc clone trait[/bold] "
                "to create an editable copy."
            )
        else:
            console.print(f"[red]Trait {name!r} not found.[/red]")
        raise typer.Exit(code=1)

    if not yes:
        typer.confirm(f"Remove trait {name!r}?", abort=True)

    removed_entry = remove_entry(name)
    removed_rr = False
    if rr_path.exists():
        rr_path.unlink()
        removed_rr = True

    parts = []
    if removed_entry:
        parts.append("manifest entry")
    if removed_rr:
        parts.append("RR table")
    console.print(f"[green]✓[/green] Removed {name!r}: {', '.join(parts)}.")


# ---------------------------------------------------------------------------
# `init` — deprecated alias for `add config`
# ---------------------------------------------------------------------------

@app.command(hidden=True)
def init(
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output path (default: asked interactively)."),
    ] = None,
) -> None:
    """[Deprecated] Use 'heredicalc add config' instead."""
    console.print(
        "[yellow]Warning:[/yellow] 'heredicalc init' is deprecated. "
        "Use [bold]heredicalc add config[/bold] instead."
    )
    _add_config_wizard(output)


# ---------------------------------------------------------------------------
# `plugins` command group
# ---------------------------------------------------------------------------

plugins_app = typer.Typer(help="Manage HerediCalc plugins.")
app.add_typer(plugins_app, name="plugins")


@plugins_app.command("list")
def plugins_list(
    kind: Annotated[Optional[str], typer.Option("--kind", "-k", help="Filter by plugin kind.")] = None,
    source: Annotated[
        Optional[str], typer.Option(help="Filter by source: builtin, copyin, entrypoint.")
    ] = None,
) -> None:
    """List registered plugins."""
    registry = _build_registry()
    entries = registry.list_plugins(kind)
    if source:
        entries = [e for e in entries if e.source == source]

    table = Table("Kind", "Name", "Version", "Source", "Description")
    for e in sorted(entries, key=lambda x: (x.meta.kind, x.meta.name)):
        table.add_row(e.meta.kind, e.meta.name, e.meta.version, e.source, e.meta.description)
    console.print(table)


@plugins_app.command("validate")
def plugins_validate(
    name: Annotated[str, typer.Argument(help="Plugin name to validate.")],
) -> None:
    """Validate a plugin's interface compliance and API compatibility."""
    registry = _build_registry()
    matches = [e for e in registry.list_plugins() if e.meta.name == name]
    if not matches:
        console.print(f"[red]Plugin {name!r} not found.[/red]")
        raise typer.Exit(code=1)
    for entry in matches:
        console.print(
            f"[green]✓[/green] {entry.meta.kind}/{entry.meta.name} v{entry.meta.version} "
            f"(source={entry.source})"
        )


if __name__ == "__main__":
    app()
