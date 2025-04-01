FROM python:3.8-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY . /app/

# Installer les dépendances
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev && \
    pip install --no-cache-dir flask

# Définir les variables d'environnement
ENV PYTHONUNBUFFERED=1

# Commande par défaut (utiliser l'interface web ou la ligne de commande)
ENTRYPOINT ["python"]
CMD ["-m", "glpwnme"]
