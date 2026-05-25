#!/usr/bin/env python3
"""
Generate STATIC_FILES_VERSION dict entries for a list of GLPI versions.

Usage:
    python scripts/gen_static_fingerprints.py <releases_dir> [--baseline <version>]

    releases_dir: directory containing extracted GLPI releases as subdirs
                  named glpi-<version> (e.g. glpi-11.0.2, glpi-11.0.3, ...)

    --baseline: version to diff against for the first discovered version.
                Must also be present in releases_dir.
                Defaults to auto (each version is diffed against the previous one).

Example:
    python scripts/gen_static_fingerprints.py ~/glpi-releases --baseline 11.0.1
"""

import argparse
import hashlib
import sys
from pathlib import Path
from packaging.version import Version


# Candidate paths are URL-relative (as the web server serves them).
# GLPI < 11: files live at  <root>/js/...
# GLPI 11+:  files live at  <root>/public/js/... but are served as /js/...
JS_CANDIDATES = [
    # classic JS (10.x and 11.x)
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
    # 11.x additions
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


def sha1_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def find_release_dir(releases_dir: Path, version: str) -> Path | None:
    for candidate in [
        releases_dir / f"glpi-{version}",
        releases_dir / version,
    ]:
        if candidate.is_dir():
            return candidate
    return None


def resolve_disk_path(release_dir: Path, url_rel: str) -> Path | None:
    """
    Given a URL-relative path like 'js/common.js', find the actual file on disk.
    Tries public/<url_rel> first (GLPI 11.x layout), then <url_rel> directly (GLPI 10.x).
    """
    for prefix in ["public", ""]:
        p = release_dir / prefix / url_rel if prefix else release_dir / url_rel
        if p.exists():
            return p
    return None


def get_changed_files(dir_a: Path, dir_b: Path) -> dict[str, str]:
    """
    Return candidates that changed between dir_a and dir_b,
    keyed by URL-relative path, valued by SHA1 hash in dir_b.
    """
    changed = {}
    for rel in JS_CANDIDATES:
        fa = resolve_disk_path(dir_a, rel)
        fb = resolve_disk_path(dir_b, rel)
        if fb is None:
            continue
        if fa is None:
            changed[rel] = sha1_file(fb)
        elif sha1_file(fa) != sha1_file(fb):
            changed[rel] = sha1_file(fb)
    return changed


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("releases_dir", type=Path)
    parser.add_argument(
        "--baseline",
        help="Version to diff the first discovered version against (must also be in releases_dir)",
    )
    args = parser.parse_args()

    releases_dir: Path = args.releases_dir.expanduser().resolve()
    if not releases_dir.is_dir():
        print(f"Error: {releases_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    versions = []
    for p in releases_dir.iterdir():
        name = p.name
        ver_str = name.removeprefix("glpi-") if name.startswith("glpi-") else name
        try:
            Version(ver_str)
            versions.append(ver_str)
        except Exception:
            pass
    versions.sort(key=Version)

    if not versions:
        print(f"Error: no versioned subdirs found in {releases_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found versions: {', '.join(versions)}\n")

    results: dict[str, dict[str, str]] = {}

    for i, ver in enumerate(versions):
        ver_dir = find_release_dir(releases_dir, ver)
        if ver_dir is None:
            print(f"Warning: could not locate dir for {ver}", file=sys.stderr)
            continue

        if args.baseline and i == 0:
            baseline_ver = args.baseline
        elif i == 0:
            print(f"Skipping {ver} — no previous version to diff against (use --baseline)")
            continue
        else:
            baseline_ver = versions[i - 1]

        baseline_dir = find_release_dir(releases_dir, baseline_ver)
        if baseline_dir is None:
            print(f"Warning: baseline dir for {baseline_ver} not found, skipping {ver}", file=sys.stderr)
            continue

        changed = get_changed_files(baseline_dir, ver_dir)
        results[ver] = changed
        print(f"{ver} (diff vs {baseline_ver}): {len(changed)} changed file(s)")
        for f in changed:
            print(f"  {f}")

    print("\n\n# ---- Paste into STATIC_FILES_VERSION ----\n")
    for ver, files in results.items():
        if not files:
            print(f'        # {ver}: no tracked JS files changed vs previous version')
            continue
        print(f'        "{ver}": {{')
        for path, digest in files.items():
            print(f'            "{path}": "{digest}",')
        print("        },")


if __name__ == "__main__":
    main()
