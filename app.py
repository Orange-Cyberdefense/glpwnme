import os
import subprocess
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/run', methods=['POST'])
def run_glpwnme():
    target = request.form.get('target', '')
    action = request.form.get('action', 'check-all')
    exploit = request.form.get('exploit', '')
    options = request.form.get('options', '')
    credentials = {}
    
    if request.form.get('username'):
        credentials['username'] = request.form.get('username')
    if request.form.get('password'):
        credentials['password'] = request.form.get('password')
    if request.form.get('cookie'):
        credentials['cookie'] = request.form.get('cookie')
    
    # Construire la commande
    cmd = ["python", "-m", "glpwnme", "-t", target]
    
    if exploit:
        cmd.extend(["-e", exploit])
    
    if action == "check":
        cmd.append("--check")
    elif action == "run":
        cmd.append("--run")
    elif action == "check-all":
        cmd.append("--check-all")
    elif action == "list-plugins":
        cmd.append("--list-plugins")
    elif action == "infos":
        cmd.append("--infos")
    
    if "no-opsec" in options:
        cmd.append("--no-opsec")
    
    # Ajouter les options
    option_items = [o.strip() for o in options.split(',') if o.strip() and '=' in o.strip()]
    if option_items and action == "run":
        cmd.append("-O")
        for opt in option_items:
            cmd.append(opt)
    
    # Ajouter les identifiants
    if 'username' in credentials and 'password' in credentials:
        cmd.extend(["-u", credentials['username'], "-p", credentials['password']])
    elif 'cookie' in credentials:
        cmd.extend(["--cookie", credentials['cookie']])
    
    try:
        # Exécuter la commande
        result = subprocess.run(cmd, capture_output=True, text=True)
        return jsonify({
            'success': True,
            'command': ' '.join(cmd),
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/logs')
def get_logs():
    try:
        with open('log.glpwnme', 'r') as f:
            log_content = f.read()
        return jsonify({
            'success': True,
            'content': log_content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
