from conftest import *
from glpwnme.exploits.utils import GlpiUtils

NO_REDIRECT_JSON = discover_fixture_files("*helpdesk_no_redirect.json")
LOGIN_PAGES = discover_fixture_files("index.html", "plugins")
AUTH_PAGES = discover_fixture_files("helpdesk.html", "auth")

@pytest.mark.parametrize("version_and_path", NO_REDIRECT_JSON)
def test_extract_redirect_url_from_html(glpi_session, version_and_path):
    version, path = version_and_path

    glpi_session.sess.get = MagicMock(return_value=load_response_fixture(path))
    glpi_session.sess.post = MagicMock(return_value=load_response_fixture(path))

    result = GlpiUtils.extract_redirect(glpi_session.get("/index.php"))

    version_in_use = int(version.split(".")[0])
    if version_in_use < 11:
        assert result.startswith("/front/helpdesk.public.php") # post-only redirected to helpdesk
    elif version_in_use >= 11:
        assert result.startswith("/Helpdesk") # post-only redirected to helpdesk

@pytest.mark.parametrize("version_and_path", LOGIN_PAGES)
def test_get_plugins(version_and_path):
    version, path = version_and_path
    result = GlpiUtils.extract_plugins(path.read_text())
    version_in_use = int(version.split(".")[0])

    if version_in_use == 9:
        assert not result
    elif version_in_use == 10:
        assert result == ['archimap', 'formcreator', 'mreporting']
    else:
        assert result == ['accounts', 'advancedforms']

@pytest.mark.parametrize("version_and_path", LOGIN_PAGES)
def test_get_login_fieldnames_and_csrf(version_and_path):
    version, path = version_and_path
    version_in_use = int(version.split(".")[0])

    fields = GlpiUtils.extract_login_field(path.read_text())

    if version_in_use < 11:
        assert fields["login"].startswith("field")
        assert fields["password"].startswith("field")
    else:
        assert fields["login"] == "login_name"
        assert fields["password"] == "login_password"

    assert GlpiUtils.extract_login_field(path.read_text()) != ""

@pytest.mark.parametrize("version_and_path", AUTH_PAGES)
def test_get_versions(version_and_path):
    version, path = version_and_path
    assert version == GlpiUtils.extract_version_from_html(path.read_text()).glpi_version
