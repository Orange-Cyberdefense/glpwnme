document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('glpwnmeForm');
    const actionSelect = document.getElementById('action');
    const exploitOptions = document.querySelector('.exploit-options');
    const commandOptions = document.querySelector('.command-options');
    const exploitSelect = document.getElementById('exploit');
    const resultsElement = document.getElementById('results');
    const loadingElement = document.getElementById('loading');
    const commandDetails = document.getElementById('commandDetails');
    const commandText = document.getElementById('commandText');
    const clearResultsBtn = document.getElementById('clearResults');
    const viewLogsBtn = document.getElementById('viewLogs');
    const logModal = new bootstrap.Modal(document.getElementById('logModal'));
    const logContent = document.getElementById('logContent');

    // Afficher/masquer les options en fonction de l'action sélectionnée
    actionSelect.addEventListener('change', function() {
        if (this.value === 'check' || this.value === 'run' || this.value === 'infos') {
            exploitOptions.classList.remove('d-none');
        } else {
            exploitOptions.classList.add('d-none');
        }

        if (this.value === 'run') {
            commandOptions.classList.remove('d-none');
        } else {
            commandOptions.classList.add('d-none');
        }
    });

    // Gérer la soumission du formulaire
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Vérifier que les champs obligatoires sont remplis
        const action = actionSelect.value;
        if ((action === 'check' || action === 'run' || action === 'infos') && !exploitSelect.value) {
            alert('Please select an exploit');
            return;
        }
        
        // Afficher le chargement
        loadingElement.classList.remove('d-none');
        resultsElement.textContent = 'Running command...';
        
        // Récupérer les données du formulaire
        const formData = new FormData(form);
        
        // Ajouter l'option no-opsec si cochée
        if (document.getElementById('no-opsec').checked) {
            formData.append('options', formData.get('options') ? formData.get('options') + ',no-opsec' : 'no-opsec');
        }
        
        // Envoyer la requête
        fetch('/api/run', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingElement.classList.add('d-none');
            
            if (data.success) {
                // Afficher la commande exécutée
                commandDetails.classList.remove('d-none');
                commandText.textContent = data.command;
                
                // Afficher les résultats
                let output = data.stdout;
                if (data.stderr) {
                    output += '\n\nErrors:\n' + data.stderr;
                }
                
                resultsElement.innerHTML = '';
                
                // Coloriser la sortie
                const lines = output.split('\n');
                lines.forEach(line => {
                    let span = document.createElement('span');
                    span.textContent = line + '\n';
                    
                    if (line.includes('[+]')) {
                        span.classList.add('success-text');
                    } else if (line.includes('[-]') || line.includes('Error') || line.includes('error')) {
                        span.classList.add('error-text');
                    } else if (line.includes('[!]') || line.includes('Warning')) {
                        span.classList.add('warning-text');
                    }
                    
                    resultsElement.appendChild(span);
                });
            } else {
                resultsElement.textContent = 'Error: ' + data.error;
            }
        })
        .catch(error => {
            loadingElement.classList.add('d-none');
            resultsElement.textContent = 'Error: ' + error.message;
        });
    });
    
    // Effacer les résultats
    clearResultsBtn.addEventListener('click', function() {
        resultsElement.textContent = 'Output will be displayed here...';
        commandDetails.classList.add('d-none');
    });
    
    // Afficher les logs
    viewLogsBtn.addEventListener('click', function() {
        fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    logContent.textContent = data.content || 'No logs found';
                } else {
                    logContent.textContent = 'Error loading logs: ' + data.error;
                }
                logModal.show();
            })
            .catch(error => {
                logContent.textContent = 'Error loading logs: ' + error.message;
                logModal.show();
            });
    });
});
