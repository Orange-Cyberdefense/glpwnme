"""
Tests for AnyAuthSession.

Mocking strategy: patch requests.Session.request (the parent class
method actually invoked via super().request(...) inside _negotiate and
request), so AnyAuthSession's own negotiation logic runs for real while
no actual network traffic occurs.
"""

import pytest
from glpwnme.exploits.utils.glpi_utils import GlpiUtils

def test_decrypt_pass_works():
    key = "7fb92553bb07ec4ec343e620e5292ab47b081f0bcb0339f36352eab42df5f4f4"
    encrypted_b64 = "LKBwbvqaUOiyyDDYrbLTZEzaae+NmMdXo17wO/da9LtG0Xd6qf6wWa0vG40jdmYgoq2CMh4lrg=="

    plaintext = GlpiUtils.decrypt(encrypted_b64, key)
    assert plaintext == b"admin123!Ad5$45"

def test_decrypt_fail():
    key = "7fb92553bb07ec4ec343e620e5292ab47b081f0bcb0339f36352eab42df5f4f4"
    encrypted_b64 = "LKBwbvqaUOiyyDDYrbLTZEzaae+NmMdXo17wO/da9LtG0Xd6qf6wWa0vG40jdmYgoq2CMh5lrg=="

    plaintext = GlpiUtils.decrypt(encrypted_b64, key)
    assert plaintext == b""
