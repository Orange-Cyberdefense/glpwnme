"""
Tests for AnyAuthSession.

Mocking strategy: patch requests.Session.request (the parent class
method actually invoked via super().request(...) inside _negotiate and
request), so AnyAuthSession's own negotiation logic runs for real while
no actual network traffic occurs.
"""

import pytest
from unittest.mock import patch, MagicMock
from http import HTTPStatus
from glpwnme.exploits.utils.glpi_server_auth import AnyAuthSession
from glpwnme.exploits.exceptions import BadCredentialsException


def make_response(status_code, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    return resp


def test_negotiates_basic_auth_and_retries_successfully():
    """
    First call gets a 401 with a Basic challenge -> session should build
    HTTPBasicAuth, mark itself negotiated, and the retry should succeed.

    Three underlying requests.Session.request calls happen on this path:
      1. the probe inside _negotiate() (gets 401)
      2. the verification retry inside _negotiate() (gets 200, with auth attached)
      3. request() itself calls super().request() again after _negotiate() returns
    """
    unauthorized = make_response(HTTPStatus.UNAUTHORIZED, {"WWW-Authenticate": "Basic realm=\"test\""})
    authorized = make_response(HTTPStatus.OK)
    final_call = make_response(HTTPStatus.OK)

    with patch("requests.Session.request", side_effect=[unauthorized, authorized, final_call]) as mock_request:
        session = AnyAuthSession(username="admin", password="secret")
        result = session.request("GET", "https://target/page")

    assert session._negotiated is True
    assert session.auth is not None
    assert session.auth.username == "admin"
    assert mock_request.call_count == 3


def test_raises_bad_credentials_when_retry_still_401():
    """
    Scheme is detected and HTTPBasicAuth is built, but the retry with
    credentials still comes back 401 -> should raise BadCredentialsException
    rather than silently returning the failed response.
    """
    unauthorized = make_response(HTTPStatus.UNAUTHORIZED, {"WWW-Authenticate": "Basic realm=\"test\""})
    still_unauthorized = make_response(HTTPStatus.UNAUTHORIZED, {"WWW-Authenticate": "Basic realm=\"test\""})

    with patch("requests.Session.request", side_effect=[unauthorized, still_unauthorized]):
        session = AnyAuthSession(username="admin", password="wrongpass")

        with pytest.raises(BadCredentialsException):
            session.request("GET", "https://target/page")


def test_no_negotiation_when_no_auth_required():
    """
    Server responds 200 on the very first probe -> no WWW-Authenticate
    challenge exists, so no auth object should be built and the session
    should just be marked negotiated with auth left as None.
    """
    ok_response = make_response(HTTPStatus.OK)

    with patch("requests.Session.request", side_effect=[ok_response, ok_response]) as mock_request:
        session = AnyAuthSession(username="admin", password="secret")
        result = session.request("GET", "https://target/public-page")

    assert session._negotiated is True
    assert session.auth is None
    assert mock_request.call_count == 2  # probe inside _negotiate, then final call from request()
