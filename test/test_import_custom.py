import pytest
from glpwnme.exploits.implementations import load_custom_exploit, merge_classes
from glpwnme.exploits.exploit import GlpiExploit
from glpwnme.exploits.implementations.cve_2025_32786 import CVE_2025_32786
import glpwnme

def test_custom_import():
    exploits = load_custom_exploit(glpwnme.exploits.implementations, GlpiExploit)
    assert len(exploits) > 20
    assert CVE_2025_32786 in exploits

def test_custom_merge():
    class CVE_2025_32786:
        cve_id = "test"

    exploits = load_custom_exploit(glpwnme.exploits.implementations, GlpiExploit)
    assert CVE_2025_32786 in merge_classes(exploits, [CVE_2025_32786])
    # Local class shall not be in loaded one
    assert CVE_2025_32786 not in merge_classes([CVE_2025_32786], exploits)
