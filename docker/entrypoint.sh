#!/bin/bash
set -e

echo "🚀 Starting OpenStack Toolbox Container..."

# Afficher les informations de démarrage
echo "📦 Version: $(python -c "import tomli; import pathlib; print(tomli.loads(pathlib.Path('/app/pyproject.toml').read_text())['project']['version'])")"
echo "🔧 Python: $(python --version)"
echo "👤 User: $(whoami)"

# Vérifier les credentials OpenStack
echo "🔐 Checking OpenStack credentials..."
if [ -z "$OS_AUTH_URL" ]; then
    echo "⚠️  Warning: OS_AUTH_URL not set"
fi

# Créer les répertoires nécessaires
mkdir -p /var/log/openstack-toolbox
mkdir -p /config

# Configurer les horaires cron depuis les variables d'environnement
echo "⏰ Configuring cron schedules..."

# Valeurs par défaut
CRON_WEEKLY_REPORT="${CRON_WEEKLY_REPORT:-0 8 * * 1}"
CRON_DAILY_SUMMARY="${CRON_DAILY_SUMMARY:-0 9 * * *}"
CRON_OPTIMIZATION="${CRON_OPTIMIZATION:-0 10 * * *}"

# Générer le fichier crontab dynamiquement
cat > /tmp/crontab << EOF
# Crontab pour OpenStack Toolbox - Généré automatiquement
# Format: minute hour day month weekday command

# Rapport hebdomadaire
${CRON_WEEKLY_REPORT} /usr/local/bin/python -m src.weekly_notification_optimization >> /var/log/openstack-toolbox/weekly-notification.log 2>&1

# Résumé quotidien
${CRON_DAILY_SUMMARY} /usr/local/bin/python -m src.openstack_summary >> /var/log/openstack-toolbox/daily-summary.log 2>&1

# Optimisation
${CRON_OPTIMIZATION} /usr/local/bin/python -m src.openstack_optimization >> /var/log/openstack-toolbox/optimization.log 2>&1

EOF

# Appliquer le crontab
crontab /tmp/crontab

echo "✅ Cron schedules configured:"
echo "   📧 Weekly report: ${CRON_WEEKLY_REPORT}"
echo "   📊 Daily summary: ${CRON_DAILY_SUMMARY}"
echo "   🔍 Optimization: ${CRON_OPTIMIZATION}"

# Démarrer cron en arrière-plan
echo "⏰ Starting cron daemon..."
cron

# Fonction pour gérer l'arrêt propre
cleanup() {
    echo "🛑 Shutting down gracefully..."
    pkill -P $$
    exit 0
}

trap cleanup SIGTERM SIGINT

# Démarrer le collecteur de métriques Prometheus en arrière-plan
echo "📊 Starting Prometheus metrics collector on port $PROMETHEUS_PORT..."
python -m src.openstack_metrics_collector &
METRICS_PID=$!

# Afficher le statut
echo "✅ Container started successfully!"
echo "📊 Prometheus metrics: http://localhost:$PROMETHEUS_PORT/metrics"
echo "⏰ Cron jobs configured and running"
echo "📝 Logs: /var/log/openstack-toolbox/"

# Garder le container actif et surveiller les processus
while true; do
    # Vérifier si le collecteur de métriques tourne toujours
    if ! kill -0 $METRICS_PID 2>/dev/null; then
        echo "❌ Metrics collector stopped unexpectedly, restarting..."
        python -m src.openstack_metrics_collector &
        METRICS_PID=$!
    fi
    
    sleep 30
done
