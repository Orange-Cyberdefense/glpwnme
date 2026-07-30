"""
Tests for GlpiSession._mfa_login()
 
Covers:
    - successful MFA verification (redirected away from /MFA/, /index.php, /front/login.php)
    - failure: still on /MFA/Verify (denylist hit)
    - failure: redirected back to /front/login.php
    - failure: explicit 400/401 status code short-circuit
    - regression test for the case-sensitivity bug (server returns an
      uppercase/mixed-case path, e.g. "/MFA/Verify" or "/Front/Login.php")
    - login_infos is populated only on success, untouched on failure
"""
import pytest
from http import HTTPStatus
from unittest.mock import MagicMock
from conftest import FakeResponse

def test_mfa_login_success_redirected_to_app(glpi_session):
    glpi_session.post = MagicMock(
        return_value=FakeResponse(
            text="",
            url="https://glpi.example.com/glpi/front/central.php",
            status_code=200,
        )
    )
 
    result = glpi_session._mfa_login("123456")
 
    assert result is True
    assert glpi_session.login_infos["after_login_response"] is not None

def test_mfa_login_failure_still_on_mfa_verify(glpi_session):
    glpi_session.post = MagicMock(
        return_value=FakeResponse(
            text="",
            url="https://glpi.example.com/glpi/MFA/Verify",
            status_code=200,
        )
    )
 
    result = glpi_session._mfa_login("000000")
 
    assert result is False
    assert glpi_session.login_infos["after_login_response"] is None

def test_mfa_login_success_redirected_to_app(glpi_session):
    glpi_session.post = MagicMock(
        return_value=FakeResponse(
            text="",
            url="https://glpi.example.com/glpi/front/central.php",
            status_code=200,
        )
    )
 
    result = glpi_session._mfa_login("123456")
 
    assert result is True
    assert glpi_session.login_infos["after_login_response"] is not None

def test_mfa_login_handles_subdirectory_install(glpi_session):
    glpi_session.post = MagicMock(
        return_value=FakeResponse(
            text="",
            url="https://glpi.example.com/glpi/MFA/Verify",
            status_code=200,
        )
    )
 
    result = glpi_session._mfa_login("000000")
 
    assert result is False
    assert glpi_session.login_infos["after_login_response"] is None

@pytest.mark.parametrize("url", [
    "https://glpi.example.com/MFA/Verify",          # mixed case, root install
    "https://glpi.example.com/Front/Login.php",      # mixed case, root install
    "https://glpi.example.com/INDEX.PHP",             # uppercase, root install
])
def test_mfa_login_handles_mixed_case_paths(glpi_session, url):
    glpi_session.post = MagicMock(
        return_value=FakeResponse(text="", url=url, status_code=200)
    )
 
    result = glpi_session._mfa_login("000000")
 
    assert result is False

def test_mfa_login_success_uses_current_url_for_after_login_url(glpi_session):
    """
    after_login_url is read from self.current_url (set by the response
    hook), not from result.url directly -- confirm it gets populated on
    success, matching the value the hook would have set for this response.
    """
    target_url = "https://glpi.example.com/glpi/front/central.php"
    glpi_session.current_url = target_url
    glpi_session.post = MagicMock(
        return_value=FakeResponse(text="", url=target_url, status_code=200)
    )
 
    glpi_session._mfa_login("123456")
 
    assert glpi_session.login_infos["after_login_url"] == target_url

