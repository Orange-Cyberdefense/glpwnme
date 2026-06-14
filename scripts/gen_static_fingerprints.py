#!/usr/bin/env python3
"""
Generate STATIC_FILES_VERSION dict entries from a local GLPI git clone.

For each requested version, selects the most discriminating JS files — those
whose SHA1 hash appears in the fewest other versions. Globally unique files
(hash found in exactly one version) are preferred. When two versions share all
file hashes, they are flagged as ambiguous and get identical entries; the
detection algorithm will return both as candidates at runtime.

Usage:
    python scripts/gen_static_fingerprints.py <glpi_repo> [--tags VERSION ...]

    glpi_repo: path to a local clone of https://github.com/glpi-project/glpi
    --tags:    version strings to emit entries for (e.g. 10.0.18 11.0.7).
               Defaults to all glpi-10.* and glpi-11.* tags found in the repo.

Maintainability workflow for a new GLPI release:
    cd ~/glpi-repo && git fetch --tags
    python scripts/gen_static_fingerprints.py ~/glpi-repo --tags 11.0.8
    # paste the output into glpi_static_files_version.py

The clone stays on the maintainer's machine and is never committed to glpwnme.
"""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from packaging.version import Version


JS_CANDIDATES = [
    "js/common.js",
    "js/common_ajax_controller.js",
    "js/dashboard.js",
    "js/fileupload.js",
    "js/impact.js",
    "js/planning.js",
    "js/clipboard.js",
    "js/glpi_dialog.js",
    "js/misc.js",
    "js/modules/Kanban/Kanban.js",
    "js/modules/Debug/Debug.js",
    "js/Forms/FaIconSelector.js",
    "js/RichText/ContentTemplatesParameters.js",
    "js/RichText/UserMention.js",
    "js/RichText/FormTags.js",
    "js/modules/Forms/EditorController.js",
    "js/modules/Forms/RendererController.js",
    "js/modules/Forms/BaseConditionEditorController.js",
    "js/modules/Forms/QuestionSelectable.js",
    "js/modules/Forms/DestinationAccordionController.js",
    "js/modules/Forms/ServiceCatalogController.js",
    "js/modules/Knowbase.js",
    "js/modules/Dashboard/Dashboard.js",
    "js/stencil-editor.js",
    "js/flatpickr_buttons_plugin.js",
    "js/notifications_ajax.js",
    "js/rack.js",
    "js/reservations.js",
]

MAX_FILES_PER_VERSION = 3


def git_show(repo: Path, tag: str, git_path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{tag}:{git_path}"],
        cwd=repo,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def sha1(content: bytes) -> str:
    return hashlib.sha1(content).hexdigest()


def get_file_hash(repo: Path, tag: str, url_rel: str) -> str | None:
    """
    Read url_rel from the git tag. Tries public/<url_rel> first (GLPI 11.x layout
    where files live under public/ but are served without the prefix), then
    <url_rel> directly (GLPI 10.x).
    """
    for git_path in [f"public/{url_rel}", url_rel]:
        content = git_show(repo, tag, git_path)
        if content is not None:
            return sha1(content)
    return None


def list_version_tags(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "tag", "-l", "10.*", "11.*"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    versions = []
    for line in result.stdout.splitlines():
        ver_str = line.strip()
        if "-" in ver_str:  # skip pre-releases (betas, RCs)
            continue
        try:
            Version(ver_str)
            versions.append(ver_str)
        except Exception:
            pass
    versions.sort(key=Version)
    return versions


def build_matrix(repo: Path, versions: list[str]) -> dict[str, dict[str, str | None]]:
    """Build a version x file -> sha1 | None matrix from the git clone."""
    matrix: dict[str, dict[str, str | None]] = {}
    for ver in versions:
        tag = ver
        print(f"  reading {tag}...", file=sys.stderr)
        matrix[ver] = {url_rel: get_file_hash(repo, tag, url_rel) for url_rel in JS_CANDIDATES}
    return matrix


def find_discriminating_files(
    matrix: dict[str, dict[str, str | None]],
    target_versions: list[str],
) -> dict[str, dict[str, str]]:
    """
    For each target version V, use greedy set cover to pick up to
    MAX_FILES_PER_VERSION files that collectively have a different hash in as
    many other versions as possible. A version W "covered" by at least one
    chosen file will fail V's entry check on a W container, preventing false
    matches. Versions that remain uncovered after MAX_FILES_PER_VERSION files
    are genuinely ambiguous and flagged by check_system_ambiguities.
    """
    all_versions = list(matrix.keys())

    result: dict[str, dict[str, str]] = {}
    for ver in target_versions:
        ver_files = {f: h for f, h in matrix[ver].items() if h is not None}

        if not ver_files:
            print(f"  WARNING: {ver} — no candidate files found", file=sys.stderr)
            result[ver] = {}
            continue

        # For each file, which other versions have a different hash?
        file_blocks: dict[str, set[str]] = {
            f: {w for w in all_versions if w != ver and matrix[w].get(f) != h}
            for f, h in ver_files.items()
        }

        chosen: dict[str, str] = {}
        uncovered = set(all_versions) - {ver}

        for _ in range(MAX_FILES_PER_VERSION):
            if not uncovered:
                break
            best = max(
                (f for f in ver_files if f not in chosen),
                key=lambda f: len(file_blocks[f] & uncovered),
                default=None,
            )
            if best is None or not (file_blocks[best] & uncovered):
                break
            chosen[best] = ver_files[best]
            uncovered -= file_blocks[best]

        result[ver] = chosen

    return result


def check_system_ambiguities(
    entries: dict[str, dict[str, str]],
    matrix: dict[str, dict[str, str | None]],
    target_versions: list[str],
) -> dict[str, list[str]]:
    """
    For each target version, find other versions whose entry would also fully
    match a container running that version — i.e. genuine detection-time ties.
    Returns {version: [conflicting versions]}.
    """
    ambiguities: dict[str, list[str]] = {}
    for ver in target_versions:
        conflicts = [
            other_ver
            for other_ver, other_files in entries.items()
            if other_ver != ver
            and other_files
            and all(matrix[ver].get(file) == h for file, h in other_files.items())
        ]
        if conflicts:
            ambiguities[ver] = sorted(conflicts, key=Version)
    return ambiguities


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("glpi_repo", type=Path, help="Path to local GLPI git clone")
    parser.add_argument(
        "--tags",
        nargs="+",
        metavar="VERSION",
        help="Version strings to emit (e.g. 10.0.18 11.0.7). "
             "Defaults to all glpi-10.* and glpi-11.* tags.",
    )
    args = parser.parse_args()

    repo: Path = args.glpi_repo.expanduser().resolve()
    if not (repo / ".git").exists() and not (repo / "HEAD").exists():
        print(f"Error: {repo} does not look like a git repository", file=sys.stderr)
        sys.exit(1)

    print("Discovering tags...", file=sys.stderr)
    all_versions = list_version_tags(repo)
    if not all_versions:
        print("Error: no glpi-10.* or glpi-11.* tags found", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(all_versions)} version tags: {', '.join(all_versions)}", file=sys.stderr)

    target_versions = args.tags if args.tags else all_versions
    unknown = [v for v in target_versions if v not in all_versions]
    for v in unknown:
        print(f"Warning: glpi-{v} not found in repository tags, skipping", file=sys.stderr)
    target_versions = [v for v in target_versions if v in all_versions]

    if not target_versions:
        print("Error: no valid target versions", file=sys.stderr)
        sys.exit(1)

    print(f"\nBuilding hash matrix for all {len(all_versions)} versions...", file=sys.stderr)
    matrix = build_matrix(repo, all_versions)

    print("\nSelecting discriminating files...", file=sys.stderr)
    entries = find_discriminating_files(matrix, target_versions)

    ambiguities = check_system_ambiguities(entries, matrix, target_versions)
    for ver, conflicts in sorted(ambiguities.items(), key=lambda x: Version(x[0])):
        print(
            f"  NOTE: {ver} cannot be distinguished from {', '.join(conflicts)} "
            f"at detection time — both entries will match",
            file=sys.stderr,
        )

    print("\n\n# ---- Paste into STATIC_FILES_VERSION ----\n")
    for ver in sorted(target_versions, key=Version):
        files = entries.get(ver, {})
        if not files:
            print(f'        # {ver}: no discriminating files found')
            continue
        print(f'        "{ver}": {{')
        for file, h in files.items():
            print(f'            "{file}": "{h}",')
        print("        },")


if __name__ == "__main__":
    main()
