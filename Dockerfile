# Dockerfile pour OpenStack Metrics Collector
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="loutre@ikmail.com"
LABEL description="OpenStack Metrics Collector - Prometheus Exporter"
LABEL version="1.5.0"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PROMETHEUS_PORT=8000

# Créer un utilisateur non-root
RUN useradd -m -u 1000 -s /bin/bash openstack && \
    mkdir -p /app /config && \
    chown -R openstack:openstack /app /config

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires pour l'installation
COPY --chown=openstack:openstack pyproject.toml README.md ./
COPY --chown=openstack:openstack src/ ./src/

# Installer le package et ses dépendances
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Changer vers l'utilisateur non-root
USER openstack

# Exposer le port Prometheus
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/metrics')" || exit 1

# Point d'entrée
ENTRYPOINT ["python", "-m", "src.openstack_metrics_collector"]
