"""
Glob-discovered login fixture tests.

Rather than hardcoding "login_success.json" / "login_failure.json" as the
only fixtures per version, this discovers ANY file matching
login_success_*.json / login_failure_*.json under each version's
fixtures/<version>/login/ directory, and turns each match into its own
parametrized test case.

This means: to add a new success/failure scenario for a version (e.g.
login_success_token.json, login_success_remember_me.json,
login_failure_locked_account.json), you just drop the file in -- no test
code changes needed, and each file shows up as its own named test in
pytest's output (so a failure tells you exactly which scenario broke).

Discovery happens at COLLECTION time (module import), which is the
standard pytest pattern for "parametrize over files found on disk".
"""

import json
import pytest
from unittest.mock import MagicMock
from conftest import FakeResponse, discover_fixture_files, load_response_fixture, FIXTURES_DIR

def fixture_id(param):
    """
    Build a readable pytest test ID like '9.4.0/login_success_token' instead
    of pytest's default (which would just show the tuple repr).
    """
    version, path = param
    return f"{version}/{path.stem}"

def load_login_page(version):
    return (FIXTURES_DIR / version / "login" / "login_page.html").read_text()


SUCCESS_FIXTURES = discover_fixture_files("login_success_*.json")
FAILURE_FIXTURES = discover_fixture_files("login_failure_*.json")


# Fail loudly at collection time if discovery found nothing -- silently
# collecting 0 tests here would look like "everything passed" in CI when
# it actually means "nothing was tested at all".
if not SUCCESS_FIXTURES:
    pytest.fail(
        f"No login_success_*.json fixtures found under {FIXTURES_DIR}/<version>/login/. "
        "Did fixture files move, or is the naming pattern wrong?",
        pytrace=False,
    )

if not FAILURE_FIXTURES:
    pytest.fail(
        f"No login_failure_*.json fixtures found under {FIXTURES_DIR}/<version>/login/.",
        pytrace=False,
    )

@pytest.mark.parametrize("version_and_path", SUCCESS_FIXTURES, ids=fixture_id)
def test_login_success_fixture(glpi_session, version_and_path):
    version, path = version_and_path

    glpi_session.sess.get = MagicMock(return_value=FakeResponse(text=load_login_page(version)))
    glpi_session.sess.post = MagicMock(return_value=load_response_fixture(path))

    result = glpi_session.login("admin", "correct-password")

    assert result is True, f"Expected login() to succeed for fixture {path}"
    assert glpi_session.login_infos["after_login_response"] is not None


@pytest.mark.parametrize("version_and_path", FAILURE_FIXTURES, ids=fixture_id)
def test_login_failure_fixture(glpi_session, version_and_path):
    version, path = version_and_path

    glpi_session.sess.get = MagicMock(return_value=FakeResponse(text=load_login_page(version)))
    glpi_session.sess.post = MagicMock(return_value=load_response_fixture(path))

    result = glpi_session.login("admin", "wrong-password")

    assert result is False, f"Expected login() to fail for fixture {path}"
    assert glpi_session.login_infos["after_login_response"] is None
