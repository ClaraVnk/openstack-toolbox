#!/bin/bash
# Script de test pour vérifier le bon fonctionnement du container standalone

set -e

echo "🧪 Testing OpenStack Toolbox Standalone Container..."
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de test
test_command() {
    local description="$1"
    local command="$2"
    
    echo -n "Testing: $description... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Vérifier que le container tourne
test_command "Container is running" \
    "docker ps | grep -q openstack-toolbox"

# Vérifier que cron tourne
test_command "Cron daemon is running" \
    "docker exec openstack-toolbox pgrep cron"

# Vérifier que le collecteur de métriques tourne
test_command "Metrics collector is running" \
    "docker exec openstack-toolbox pgrep -f openstack_metrics_collector"

# Vérifier que le port Prometheus est accessible
test_command "Prometheus port is accessible" \
    "curl -f http://localhost:8000/metrics"

# Vérifier que les tâches cron sont configurées
test_command "Cron jobs are configured" \
    "docker exec openstack-toolbox crontab -l | grep -q weekly_notification"

# Vérifier que les répertoires de logs existent
test_command "Log directories exist" \
    "docker exec openstack-toolbox test -d /var/log/openstack-toolbox"

# Vérifier que Python et les modules sont installés
test_command "Python modules are installed" \
    "docker exec openstack-toolbox python -c 'import src.openstack_metrics_collector'"

# Vérifier les variables d'environnement OpenStack
test_command "OpenStack credentials are set" \
    "docker exec openstack-toolbox env | grep -q OS_AUTH_URL"

# Healthcheck
test_command "Container healthcheck passes" \
    "docker inspect openstack-toolbox --format='{{.State.Health.Status}}' | grep -q healthy"

echo ""
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "📊 Container stats:"
docker stats openstack-toolbox --no-stream

echo ""
echo "📝 Recent logs:"
docker logs openstack-toolbox --tail 20

echo ""
echo -e "${GREEN}Container is ready to use!${NC}"
