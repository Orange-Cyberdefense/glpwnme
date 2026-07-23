"""
Shared fixtures for GlpiSession tests.

Strategy: mock at the HTTP boundary (self.sess.get / self.sess.post),
not deeper. We build lightweight fake Response objects exposing exactly
what the production code touches (.text, .content, .url, .status_code,
.headers), so GlpiUtils' real parsing logic (BeautifulSoup, regex, etc.)
runs unmodified against realistic HTML fixtures. No live GLPI instance,
no real network calls.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from glpwnme.exploits.utils.glpi_session import GlpiSession
from glpwnme.exploits.utils.glpi_utils import GlpiCredentials

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class FakeResponse:
    """
    Minimal stand-in for requests.Response, exposing only what
    GlpiSession / GlpiUtils actually read.
    """
    def __init__(self, text="", url="https://glpi.example.com/glpi/front/login.php",
                 status_code=200, headers=None, request_body=None, request_method="POST"):
        self.text = text
        self.content = text.encode() if isinstance(text, str) else text
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}

        # Minimal fake of response.request, used by GlpiSession.custom_hook
        self.request = MagicMock()
        self.request.body = request_body
        self.request.method = request_method
        self.request.headers = {}

@pytest.fixture
def credentials():
    return GlpiCredentials(
        username="glpi",
        password="glpi",
        server_user="",
        server_password="",
    )

@pytest.fixture
def glpi_session(credentials):
    """
    A GlpiSession with its underlying AnyAuthSession's get/post replaced
    by MagicMocks, so no real HTTP traffic is ever sent. We patch
    AnyAuthSession itself so __init__ doesn't try to do anything network
    related either.
    """
    with patch("glpwnme.exploits.utils.glpi_session.GlpiSession") as MockSession:
        mock_sess_instance = MagicMock()
        mock_sess_instance.cookies.get_dict.return_value = {}
        mock_sess_instance.hooks = {"response": []}
        MockSession.return_value = mock_sess_instance

        session = GlpiSession(
            target="https://glpi.example.com/glpi/",
            credentials=credentials
        )
        yield session

def discover_fixture_files(pattern, category="login"):
    """
    Find all files matching `pattern` (e.g. "login_success_*.json") across
    every version directory, returning a list of (version, path) tuples.

    Versions are discovered dynamically too -- any directory directly
    under fixtures/ that contains a login/ subdir is treated as a GLPI
    version, so adding a new version directory is also test-code-free.
    """
    results = []
    for version_dir in sorted(FIXTURES_DIR.iterdir()):
        if not version_dir.is_dir():
            continue  # skip _TEMPLATE_*.json etc at the top level
        cat_dir = version_dir / category
        if not cat_dir.is_dir():
            continue
        for fixture_file in sorted(cat_dir.glob(pattern)):
            results.append((version_dir.name, fixture_file))
    return results

def load_response_fixture(path):
    data = json.loads(path.read_text())
    return FakeResponse(
        text=data.get("text", ""),
        url=data.get("url", ""),
        status_code=data.get("status_code", 200),
        headers=data.get("headers", {}),
    )

