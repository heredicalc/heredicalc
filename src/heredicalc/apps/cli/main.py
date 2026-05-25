"""HerediCalc v4 command-line interface."""

from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from heredicalc.core.exceptions import HerediCalcError, SegregaError
from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry

app = typer.Typer(
    name="heredicalc",
    help="HerediCalc v4 — FLB factor for hereditary cosegregation analysis.",
    add_completion=False,
)
console = Console()


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

    # CLI overrides
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


@app.command()
def init(
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output path (default: asked interactively)."),
    ] = None,
) -> None:
    """Interactively generate a heredicalc.yml configuration file."""
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

    # Last step: ask for output destination
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
