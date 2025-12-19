# Dockerfile pour OpenStack Toolbox
# Suite complète avec métriques Prometheus + tâches cron automatisées
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="loutre@ikmail.com"
LABEL description="OpenStack Toolbox - Complete Suite with Cron"
LABEL version="1.6.1"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PROMETHEUS_PORT=8000
ENV DEBIAN_FRONTEND=noninteractive

# Installer cron et les dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m -u 1000 -s /bin/bash openstack && \
    mkdir -p /app /config /var/log/openstack-toolbox && \
    chown -R openstack:openstack /app /config /var/log/openstack-toolbox

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires pour l'installation
COPY --chown=openstack:openstack pyproject.toml README.md ./
COPY --chown=openstack:openstack src/ ./src/

# Installer le package et ses dépendances
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copier le fichier crontab et le script d'entrypoint
COPY --chown=openstack:openstack docker/crontab /etc/cron.d/openstack-toolbox
COPY --chown=openstack:openstack docker/entrypoint.sh /usr/local/bin/entrypoint.sh

# Configurer les permissions
RUN chmod 0644 /etc/cron.d/openstack-toolbox && \
    chmod +x /usr/local/bin/entrypoint.sh && \
    crontab -u openstack /etc/cron.d/openstack-toolbox

# Créer le répertoire pour les logs cron
RUN touch /var/log/cron.log && \
    chown openstack:openstack /var/log/cron.log

# Exposer le port Prometheus
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

# Point d'entrée
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
