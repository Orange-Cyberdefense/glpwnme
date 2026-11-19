"""
Self-contained pytest file (stdlib + pytest only).

The function under test is copied below in the "UNDER TEST" section. To test your real code
instead, delete that section and import `GlpiStaticFilesVersion` and the method from your
project (see the FakeGlpi class).
"""
import random
import types
from collections import Counter
from hashlib import sha1

import pytest


# ----------------------------------------------------------------------------------------
# UNDER TEST
# ----------------------------------------------------------------------------------------
class GlpiStaticFilesVersion:
    STATIC_FILES_VERSION = {}


def _find_version_from_static(self):
    """
    Identify the most probable GLPI version using static files SHA1.

    Set the version and how it was found on success
    """
    versions = GlpiStaticFilesVersion.STATIC_FILES_VERSION
    if not versions:
        return False
    key = lambda v: tuple(map(int, v.split(".")))

    # hash of a file at version V = last hash listed at a version <= V
    states, current = {}, {}
    for v in sorted(versions, key=key):
        current.update(versions[v])
        states[v] = dict(current)

    request_cache = {}
    match = dict.fromkeys(states, 0)
    miss = dict.fromkeys(states, 0)

    def check(path):
        r = self.get(f"/{path}")
        if r is None or r.status_code != 200:
            request_cache[path] = None
            for v, files in states.items():
                if path in files:
                    miss[v] += 1
            return
        digest = sha1(r.content).hexdigest()
        request_cache[path] = digest
        for v, files in states.items():
            if path in files:
                if files[path] == digest:
                    match[v] += 1
                else:
                    miss[v] += 1

    def candidates():
        best = min((miss[v], -match[v]) for v in states)
        return [v for v in states if (miss[v], -match[v]) == best]

    check("js/common.js")
    found = candidates()

    while len(found) > 1:
        scored = []
        for path in {p for v in found for p in states[v]} - request_cache.keys():
            groups = Counter(states[v].get(path) for v in found)
            if len(groups) > 1:
                scored.append((len(groups), -max(groups.values()), path))
        if not scored:
            break
        check(max(scored)[2])
        found = candidates()

    if match[found[0]] == 0:
        return False

    found.sort(key=key)
    if len(found) > 1:
        self.glpi_infos.glpi_version_candidates = found

    self.glpi_infos.glpi_version = found[0]
    self.glpi_infos.glpi_version_reason = "Version found from static files analysis"
    return True


# ----------------------------------------------------------------------------------------
# TEST HELPERS
# ----------------------------------------------------------------------------------------
class FakeGlpi:
    """Fake target: `files` maps a path to the file body (bytes); missing path -> 404."""

    find = _find_version_from_static

    def __init__(self, files=None, getter=None):
        self.files = files or {}
        self.getter = getter
        self.requests = []
        self.glpi_infos = types.SimpleNamespace(
            glpi_version=None, glpi_version_candidates=None, glpi_version_reason=None
        )

    def get(self, path):
        self.requests.append(path.lstrip("/"))
        if self.getter:
            return self.getter(path)
        body = self.files.get(path.lstrip("/"))
        if body is None:
            return types.SimpleNamespace(status_code=404, content=b"")
        return types.SimpleNamespace(status_code=200, content=body)

    @property
    def version(self):
        return self.glpi_infos.glpi_version

    @property
    def candidates(self):
        return self.glpi_infos.glpi_version_candidates


def sha(label):
    return sha1(label.encode()).hexdigest()


def key(version):
    return tuple(map(int, version.split(".")))


# Readable labels instead of real hashes: the target serves the label, the dictionary stores sha1(label).
LABELS = {
    "9.5.8": {"js/common.js": "c1", "js/fileupload.js": "f1", "js/clipboard.js": "k1"},
    "9.5.9": {"js/common.js": "c1", "js/fileupload.js": "f1", "js/clipboard.js": "k1"},
    "9.5.10": {"js/common.js": "c1", "js/fileupload.js": "f2", "js/clipboard.js": "k1"},
    "9.5.11": {"js/common.js": "c1", "js/fileupload.js": "f2", "js/clipboard.js": "k1"},
    "9.5.12": {"js/common.js": "c1", "js/fileupload.js": "f2", "js/clipboard.js": "k1"},
    "9.5.13": {"js/common.js": "c1", "js/fileupload.js": "f2", "js/clipboard.js": "k1"},
    "10.0.0": {"js/Forms/FaIconSelector.js": "i1", "js/RichText/ContentTemplatesParameters.js": "t1", "js/RichText/UserMention.js": "u1"},
    "10.0.1": {"js/Forms/FaIconSelector.js": "i2", "js/RichText/ContentTemplatesParameters.js": "t2", "js/modules/Kanban/Kanban.js": "n1"},
    "10.0.2": {"js/modules/Kanban/Kanban.js": "n2", "js/common.js": "c2", "js/fileupload.js": "f3"},
    "10.0.3": {"js/common.js": "c3", "js/fileupload.js": "f4", "js/impact.js": "m1"},
    "10.0.4": {"js/common.js": "c4", "js/dashboard.js": "d1", "js/fileupload.js": "f5"},
    "10.0.5": {"js/Forms/FaIconSelector.js": "i2", "js/RichText/ContentTemplatesParameters.js": "t2"},
    "10.0.6": {"js/Forms/FaIconSelector.js": "i3", "js/RichText/ContentTemplatesParameters.js": "t3", "js/fileupload.js": "f6"},
    "10.0.19": {"js/impact.js": "m2", "js/planning.js": "p1"},
    "10.0.20": {"js/impact.js": "m3"},
    "10.0.21": {"js/impact.js": "m3"},
    "10.0.22": {"js/impact.js": "m3"},
    "10.0.23": {"js/common.js": "c5"},
    "10.0.24": {"js/common.js": "c5"},
    "10.0.25": {"js/common.js": "c5"},
    "11.0.0": {"js/common.js": "c6"},
    "11.0.1": {"js/common.js": "c7"},
    "11.0.2": {"js/common.js": "c8"},
    "11.0.3": {"js/common.js": "c9", "js/modules/Knowbase.js": "b1"},
    "11.0.4": {"js/modules/Knowbase.js": "b2"},
    "12.0.0": {"js/common.js": "c10"},
    "12.0.1": {"js/common.js": "c11", "js/modules/Forms/RendererController.js": "r1"},
    "12.0.2": {"js/modules/Forms/RendererController.js": "r2"},
}


def hashed(labels):
    return {v: {p: sha(label) for p, label in files.items()} for v, files in labels.items()}


def forward_fill(labels):
    states, current = {}, {}
    for v in sorted(labels, key=key):
        current.update(labels[v])
        states[v] = dict(current)
    return states


STATES = forward_fill(LABELS)  # what a target running version V actually serves


def serve(version):
    return {p: label.encode() for p, label in STATES[version].items()}


@pytest.fixture
def use_data(monkeypatch):
    def _use(labels=LABELS):
        monkeypatch.setattr(GlpiStaticFilesVersion, "STATIC_FILES_VERSION", hashed(labels))
    _use()
    return _use


def run(files=None, getter=None):
    target = FakeGlpi(files, getter)
    return target, target.find()


# ----------------------------------------------------------------------------------------
# TESTS
# ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("version", sorted(LABELS, key=key))
def test_every_version_is_found(use_data, version):
    target, ok = run(serve(version))
    same = sorted((w for w in STATES if STATES[w] == STATES[version]), key=key)

    assert ok is True
    assert target.version == same[0]
    assert version in (target.candidates or [target.version])
    assert (target.candidates or [same[0]]) == same
    assert target.requests[0] == "js/common.js"
    assert len(set(target.requests)) == len(target.requests)


def test_unique_version_one_request_no_candidates(use_data):
    target, ok = run(serve("11.0.1"))
    assert ok is True
    assert target.version == "11.0.1"
    assert target.candidates is None
    assert target.requests == ["js/common.js"]


@pytest.mark.parametrize(
    "served, expected",
    [
        ("10.0.21", ["10.0.20", "10.0.21", "10.0.22"]),
        ("10.0.25", ["10.0.23", "10.0.24", "10.0.25"]),
        ("9.5.9", ["9.5.8", "9.5.9"]),
        ("9.5.13", ["9.5.10", "9.5.11", "9.5.12", "9.5.13"]),
    ],
)
def test_identical_releases_return_lowest_and_all_candidates(use_data, served, expected):
    target, ok = run(serve(served))
    assert ok is True
    assert target.version == expected[0]
    assert target.candidates == expected


def test_reason_is_set(use_data):
    target, _ = run(serve("12.0.2"))
    assert target.glpi_infos.glpi_version_reason == "Version found from static files analysis"


def test_useless_files_are_not_requested(use_data):
    target, _ = run(serve("9.5.13"))
    assert "js/clipboard.js" not in target.requests  # same hash in every candidate
    assert len(target.requests) <= 3


def test_old_releases_are_not_dragged_into_candidates_of_9_5(use_data):
    # 10.0.0 / 10.0.1 inherit the 9.5.13 hashes by forward fill but do not have 10.x-only files on a 9.5 target
    target, ok = run(serve("9.5.12"))
    assert ok is True
    assert all(v.startswith("9.5.") for v in target.candidates)


def test_tolerates_server_error_on_one_file(use_data):
    files = serve("11.0.3")

    def getter(path):
        if path.endswith("modules/Knowbase.js"):
            return types.SimpleNamespace(status_code=500, content=b"boom")
        body = files.get(path.lstrip("/"))
        return types.SimpleNamespace(status_code=200 if body else 404, content=body or b"")

    target, ok = run(getter=getter)
    assert ok is True
    assert "11.0.3" in (target.candidates or [target.version])


def test_dictionary_order_does_not_matter(monkeypatch):
    items = list(hashed(LABELS).items())
    random.Random(0).shuffle(items)
    monkeypatch.setattr(GlpiStaticFilesVersion, "STATIC_FILES_VERSION", dict(items))
    target, ok = run(serve("10.0.4"))
    assert ok is True
    assert target.version == "10.0.4"


def test_empty_dictionary(monkeypatch):
    monkeypatch.setattr(GlpiStaticFilesVersion, "STATIC_FILES_VERSION", {})
    target, ok = run()
    assert ok is False
    assert target.requests == []


def test_everything_404(use_data):
    target, ok = run()
    assert ok is False
    assert target.version is None


def test_get_returns_none(use_data):
    target, ok = run(getter=lambda path: None)
    assert ok is False
    assert target.version is None


def test_same_html_page_for_every_path(use_data):
    paths = {p for files in LABELS.values() for p in files}
    target, ok = run({p: b"<html>not found</html>" for p in paths})
    assert ok is False
    assert target.version is None


def test_empty_200_bodies(use_data):
    paths = {p for files in LABELS.values() for p in files}
    target, ok = run({p: b"" for p in paths})
    assert ok is False


def test_hashes_unknown_to_the_dictionary(use_data):
    paths = {p for files in LABELS.values() for p in files}
    target, ok = run({p: f"unknown-{p}".encode() for p in paths})
    assert ok is False
    assert target.version is None


def test_single_version(monkeypatch):
    monkeypatch.setattr(GlpiStaticFilesVersion, "STATIC_FILES_VERSION", hashed({"1.0.0": {"js/common.js": "x"}}))
    target, ok = run({"js/common.js": b"x"})
    assert ok is True and target.version == "1.0.0" and len(target.requests) == 1
    _, ok = run({"js/common.js": b"y"})
    assert ok is False


def test_version_numbers_are_compared_numerically(monkeypatch):
    labels = {"9.5.9": {"js/common.js": "same"}, "9.5.10": {"js/common.js": "same"}}
    monkeypatch.setattr(GlpiStaticFilesVersion, "STATIC_FILES_VERSION", hashed(labels))
    target, ok = run({"js/common.js": b"same"})
    assert ok is True
    assert target.version == "9.5.9"  # not "9.5.10" as a plain string sort would give
    assert target.candidates == ["9.5.9", "9.5.10"]
