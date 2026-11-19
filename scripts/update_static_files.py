#!/usr/bin/env python3
import argparse
import ast
import re
import subprocess
import sys
from hashlib import sha1
from pathlib import Path

NAME = "STATIC_FILES_VERSION"
COMMON = "js/common.js"
MIN_MAJOR = 9
MAX_EXTRA = 2
MIN_EXTRA = 2


def version_key(tag):
    return tuple(int(part) for part in tag.split("."))


def git(repo, *args, text=True):
    out = subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True).stdout
    return out.decode() if text else out


def repo_tags(repo):
    tags = git(repo, "tag", "--list").split()
    tags = [t for t in tags if re.fullmatch(r"\d+(\.\d+)+", t)]
    return sorted((t for t in tags if version_key(t)[0] >= MIN_MAJOR), key=version_key)


def tree_blobs(repo, tag, prefixes):
    blobs = {}
    for line in git(repo, "ls-tree", "-r", tag, "--", *prefixes).splitlines():
        meta, path = line.split("\t", 1)
        blobs[path] = meta.split()[2]
    return blobs


def file_sha1(repo, tag, path):
    return sha1(git(repo, "show", f"{tag}:{path}", text=False)).hexdigest()


def pick_files(tag, blobs, universe):
    """common.js + 2-3 files, chosen greedily to isolate the tag among all tags."""
    mine = blobs[tag]
    same = {
        path: {t for t in universe if blobs[t].get(path) == blob}
        for path, blob in mine.items()
    }
    remaining = set(universe)
    if COMMON in mine:
        remaining &= same[COMMON]
    chosen = [COMMON] if COMMON in mine else []

    extras = []
    while len(extras) < MAX_EXTRA and (len(extras) < MIN_EXTRA or len(remaining) > 1):
        pool = [p for p in mine if p != COMMON and p not in extras]
        if not pool:
            break
        best = min(pool, key=lambda p: (len(remaining & same[p]), len(same[p]), p))
        extras.append(best)
        remaining &= same[best]
    return chosen + extras, remaining


def load(target):
    source = Path(target).read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == NAME for t in node.targets
        ):
            return source, node, ast.literal_eval(node.value)
    sys.exit(f"{NAME} not found in {target}")


def render(data, indent):
    pad = " " * indent
    lines = [f"{pad}{NAME} = {{"]
    for version in sorted(data, key=version_key):
        lines.append(f'{pad}    "{version}": {{')
        lines += [f'{pad}        "{p}": "{h}",' for p, h in data[version].items()]
        lines.append(f"{pad}    }},")
    lines.append(f"{pad}}}")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Add GLPI tags to the static files dictionary")
    parser.add_argument("--repo", required=True, help="local GLPI git repository")
    parser.add_argument("--target", default="glpi_static_files.py", help="file holding the dictionary")
    parser.add_argument("--prefix", action="append", help="tracked directory (default: js/)")
    parser.add_argument("tags", nargs="*", help=f"default: every tag from {MIN_MAJOR}.x to the latest")
    args = parser.parse_args()
    prefixes = args.prefix or ["js/"]

    universe = repo_tags(args.repo)
    tags = args.tags or universe
    blobs = {t: tree_blobs(args.repo, t, prefixes) for t in universe}
    source, node, data = load(args.target)

    for tag in sorted(tags, key=version_key):
        if tag not in blobs:
            print(f"[!] {tag}: unknown tag, skipped")
            continue
        if COMMON not in blobs[tag]:
            print(f"[!] {tag}: {COMMON} missing")
        paths, remaining = pick_files(tag, blobs, universe)
        data[tag] = {p: file_sha1(args.repo, tag, p) for p in paths}
        ambiguous = sorted(remaining - {tag}, key=version_key)
        print(f"[+] {tag}: {len(paths)} files" + (f" (still shared with {', '.join(ambiguous)})" if ambiguous else ""))

    lines = source.splitlines()
    lines[node.lineno - 1 : node.end_lineno] = render(data, node.col_offset)
    print("\n".join(lines) + "\n")
    # Path(args.target).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()