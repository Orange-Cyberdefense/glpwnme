"""
Version-matrix tests for GlpiSession.login().

Same test logic runs against real captured fixtures from each GLPI
version, so a single assertion set proves the login flow works across
9.5.7 / 10.0.8 / 11.0.2 -- without needing live instances at test time.

Fixtures expected per version under fixtures/<version>/:
    login_page.html              - GET /index.php (logged out) body
    login_success_response.json  - {status_code, url, headers, text} after
                                    a successful POST to /front/login.php
    login_failure_response.json  - same, after a failed login attempt

NOTE: fixtures are currently placeholders / awaiting real captures from
actual 9.5.7, 10.0.8 and 11.0.2 instances. Do not trust these results
until real captures replace the placeholder files.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from conftest import FakeResponse, glpi_session, load_response_fixture, FIXTURES_DIR

GLPI_VERSIONS = ["9.4.0", "10.0.18", "11.0.7"]

def load_login_page(version):
    return (FIXTURES_DIR / version / "login" / "login_page.html").read_text()

@pytest.mark.parametrize("glpi_version", GLPI_VERSIONS)
class TestLoginAcrossVersions:
    """
    One test body, run once per GLPI version via real captured fixtures.
    """
    def test_login_success(self, glpi_session, glpi_version):
        glpi_session.sess.get = MagicMock(return_value=FakeResponse(text=load_login_page(glpi_version)))
        glpi_session.sess.post = MagicMock(return_value=load_response_fixture(
            FIXTURES_DIR / glpi_version / "login" / "login_success.json"
        ))

        result = glpi_session.login("admin", "correct-password")

        assert result is True, f"Expected successful login to be detected on GLPI {glpi_version}"
        assert glpi_session.login_infos["after_login_response"] is not None

    def test_login_failure(self, glpi_session, glpi_version):
        glpi_session.sess.get = MagicMock(return_value=FakeResponse(text=load_login_page(glpi_version)))
        glpi_session.sess.post = MagicMock(return_value=load_response_fixture(
            FIXTURES_DIR / glpi_version / "login" / "login_failure.json"
        ))

        result = glpi_session.login("admin", "wrong-password")

        assert result is False, f"Expected failed login to be detected on GLPI {glpi_version}"
        assert glpi_session.login_infos["after_login_response"] is None
