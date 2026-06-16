#!/usr/bin/env python3
"""Fetch CI5 incidence data from IARC and verify it against scripts/ci5_checksums.txt.

This is a pure acquisition step: it downloads IARC's five "detailed database" ZIPs,
unpacks them, and copies the payload byte-for-byte into the plugin data directories.
No transformation, re-encoding, line-ending change, or re-sorting is performed.

The CI5 data is (c) IARC and is NOT distributed with this repository. Running this
script obtains it separately under IARC's terms (see DATA-NOTICE.md).
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CHECKSUMS = SCRIPT_DIR / "ci5_checksums.txt"
DATA_PREFIX = "src/heredicalc/plugins/incidence_sources"
USER_AGENT = "heredicalc-ci5-fetch/1.0 (+https://github.com/heredicalc/heredicalc)"
DOWNLOAD_ATTEMPTS = 3
CI5_BASE = "https://gco.iarc.fr/media/ci5/data"


@dataclass(frozen=True)
class Band:
    name: str
    url: str
    drop_cancer: bool

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


BANDS: tuple[Band, ...] = (
    Band("ci5_viii", f"{CI5_BASE}/ci5-ix/old/vol8/CI5-VIIId.zip", False),
    Band("ci5_ix", f"{CI5_BASE}/ci5-ix/old/vol9/CI5-IXd.zip", True),
    Band("ci5_x", f"{CI5_BASE}/CI5-Xd.zip", True),
    Band("ci5_xi", f"{CI5_BASE}/ci5-xi/CI5-XId.zip", False),
    Band("ci5_xii", f"{CI5_BASE}/vol12/Download/CI5-XIId.zip", False),
)


class FetchError(Exception):
    pass


def _is_kept(member: str, band: Band) -> bool:
    low = member.lower()
    if low.startswith("layout"):
        return False  # Layout.log / layout.TXT / layout_detailed.txt — never part of the data set
    # IX/X cancer.TXT omitted to mirror committed set exactly;
    # added in follow-up PR (fixes get_trait_info for IX/X).
    return not (band.drop_cancer and low == "cancer.txt")


def _band_dir(target_root: Path, band: Band) -> Path:
    return target_root / DATA_PREFIX / band.name / "data"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> dict[str, tuple[str, int]]:
    if not CHECKSUMS.is_file():
        raise FetchError(f"checksum manifest not found: {CHECKSUMS}")
    manifest: dict[str, tuple[str, int]] = {}
    for line in CHECKSUMS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        sha, size, rel = line.split(None, 2)
        manifest[rel] = (sha, int(size))
    return manifest


def _download(band: Band, dest: Path) -> None:
    req = urllib.request.Request(band.url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as fh:
                shutil.copyfileobj(resp, fh)
            tmp.replace(dest)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            tmp.unlink(missing_ok=True)
            if attempt < DOWNLOAD_ATTEMPTS:
                print(f"  download attempt {attempt} failed ({exc}); retrying...")
                time.sleep(2 * attempt)
    raise FetchError(f"failed to download {band.url}: {last}")


def _obtain_zip(band: Band, cache_dir: Path) -> Path:
    dest = cache_dir / band.filename
    if dest.is_file():
        try:
            with zipfile.ZipFile(dest) as zf:
                if zf.namelist():
                    print(f"  using cached {band.filename}")
                    return dest
        except zipfile.BadZipFile:
            dest.unlink(missing_ok=True)
    print(f"  downloading {band.url}")
    _download(band, dest)
    return dest


def _extract_band(band: Band, zip_path: Path, target_root: Path) -> int:
    out = _band_dir(target_root, band)
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise FetchError(f"corrupt entry {bad!r} in {zip_path.name}")
        for member in zf.namelist():
            if member.endswith("/") or not _is_kept(member, band):
                continue
            (out / Path(member).name).write_bytes(zf.read(member))
            written += 1
    return written


def _verify(target_root: Path, manifest: dict[str, tuple[str, int]]) -> None:
    problems: list[str] = []
    verified = 0
    for rel, (sha, size) in manifest.items():
        path = target_root / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
            continue
        actual_size = path.stat().st_size
        if actual_size != size:
            problems.append(f"size mismatch: {rel} (expected {size}, got {actual_size})")
            continue
        if _sha256(path) != sha:
            problems.append(f"checksum mismatch: {rel}")
            continue
        verified += 1

    expected_rel = set(manifest)
    for band in BANDS:
        band_dir = _band_dir(target_root, band)
        if not band_dir.is_dir():
            continue
        for path in band_dir.iterdir():
            if not path.is_file():
                continue
            rel = path.relative_to(target_root).as_posix()
            if rel not in expected_rel:
                problems.append(f"unexpected file: {rel}")

    if problems:
        preview = "\n".join(f"  - {p}" for p in problems[:25])
        more = "" if len(problems) <= 25 else f"\n  ... and {len(problems) - 25} more"
        raise FetchError(f"verification failed ({len(problems)} problem(s)):\n{preview}{more}")
    if verified != len(manifest):
        raise FetchError(f"verified {verified} files, expected {len(manifest)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=REPO_ROOT,
        help="root directory under which the data tree is written (default: repo root)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="keep downloaded ZIPs here and reuse them on re-runs (default: a temp dir)",
    )
    args = parser.parse_args(argv)

    target_root = args.target.resolve()
    try:
        manifest = _load_manifest()
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    tmp_ctx: tempfile.TemporaryDirectory[str] | None = None
    if args.cache_dir is not None:
        cache_dir = args.cache_dir.resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
    else:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="ci5_fetch_")
        cache_dir = Path(tmp_ctx.name)

    try:
        # Download and integrity-check every ZIP before writing anything to the
        # target, so a network or archive error never leaves a half-finished tree.
        print(f"target: {target_root}")
        zips: list[tuple[Band, Path]] = []
        for band in BANDS:
            print(f"[{band.name}]")
            zips.append((band, _obtain_zip(band, cache_dir)))

        total = 0
        for band, zip_path in zips:
            count = _extract_band(band, zip_path, target_root)
            total += count
            print(f"[{band.name}] copied {count} file(s)")

        print(f"verifying {len(manifest)} files against {CHECKSUMS.name} ...")
        _verify(target_root, manifest)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()

    print(f"OK: {total}/{len(manifest)} files fetched and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
