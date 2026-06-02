FROM python:3.10-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY . /app/

# Installer les dépendances
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main

# Définir les variables d'environnement
ENV PYTHONUNBUFFERED=1

# Commande par défaut pour l'outil en ligne de commande
ENTRYPOINT ["python"]
CMD ["-m", "glpwnme"]
