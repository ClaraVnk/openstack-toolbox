# 🐳 Guide Docker - OpenStack Metrics Collector

Ce guide explique comment déployer le collecteur de métriques OpenStack avec Docker.

## 📋 Prérequis

- Docker 20.10+
- Docker Compose 2.0+
- Credentials OpenStack valides

## 🚀 Démarrage rapide

### 1. Configuration des credentials

Copiez le fichier d'exemple et configurez vos credentials :

```bash
cp .env.example .env
nano .env
```

Remplissez avec vos informations OpenStack :

```env
OS_AUTH_URL=https://api.pub1.infomaniak.cloud:5000/v3
OS_PROJECT_NAME=mon-projet
OS_USERNAME=mon-utilisateur
OS_PASSWORD=mon-mot-de-passe
OS_USER_DOMAIN_NAME=default
OS_PROJECT_DOMAIN_NAME=default
```

### 2. Lancer le collecteur

```bash
# Build et démarrage
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Vérifier le statut
docker-compose ps
```

### 3. Accéder aux métriques

Les métriques Prometheus sont disponibles sur :
```
http://localhost:8000/metrics
```

## 🔧 Commandes utiles

### Gestion du conteneur

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Voir les logs
docker-compose logs -f openstack-metrics-collector

# Voir les logs en temps réel (dernières 100 lignes)
docker-compose logs -f --tail=100

# Rebuild après modification du code
docker-compose up -d --build
```

### Debugging

```bash
# Entrer dans le conteneur
docker-compose exec openstack-metrics-collector bash

# Vérifier les variables d'environnement
docker-compose exec openstack-metrics-collector env | grep OS_

# Tester la connexion OpenStack
docker-compose exec openstack-metrics-collector python -c "
from src.config import load_openstack_credentials
creds, missing = load_openstack_credentials()
print('✅ Credentials OK' if creds else f'❌ Missing: {missing}')
"
```

### Monitoring

```bash
# Healthcheck
docker inspect openstack-metrics-collector --format='{{.State.Health.Status}}'

# Statistiques de ressources
docker stats openstack-metrics-collector

# Logs d'erreurs uniquement
docker-compose logs openstack-metrics-collector | grep ERROR
```

## 📊 Intégration avec Prometheus

### Configuration Prometheus

Ajoutez cette configuration à votre `prometheus.yml` :

```yaml
scrape_configs:
  - job_name: 'openstack-metrics'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 60s
    scrape_timeout: 30s
```

### Exemple avec Docker Compose complet

```yaml
version: '3.8'

services:
  openstack-metrics-collector:
    # ... (configuration existante)
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus-data:
  grafana-data:
```

## 🔐 Sécurité

### Bonnes pratiques

1. **Ne commitez JAMAIS le fichier `.env`** avec vos credentials
2. Utilisez des secrets Docker pour la production :

```bash
echo "mon-mot-de-passe" | docker secret create os_password -
```

3. Limitez l'accès au port 8000 avec un firewall
4. Utilisez HTTPS pour Prometheus en production

### Variables d'environnement sensibles

Le conteneur utilise un utilisateur non-root (`openstack:1000`) pour plus de sécurité.

## 📈 Performance

### Limites de ressources

Par défaut, le conteneur est limité à :
- **CPU** : 1 core max, 0.5 core réservé
- **Mémoire** : 512MB max, 256MB réservé

Ajustez dans `docker-compose.yml` si nécessaire :

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
```

### Optimisation

- Les logs sont automatiquement rotatés (max 10MB, 3 fichiers)
- Le healthcheck vérifie l'état toutes les 30 secondes
- Le collecteur redémarre automatiquement en cas d'erreur

## 🐛 Dépannage

### Le conteneur ne démarre pas

```bash
# Vérifier les logs
docker-compose logs

# Vérifier la configuration
docker-compose config

# Rebuild complet
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Erreur de connexion OpenStack

```bash
# Vérifier les credentials
docker-compose exec openstack-metrics-collector env | grep OS_

# Tester manuellement
docker-compose exec openstack-metrics-collector python -c "
import openstack
conn = openstack.connect()
print(conn.authorize())
"
```

### Métriques non disponibles

```bash
# Vérifier que le port est exposé
curl http://localhost:8000/metrics

# Vérifier les logs du collecteur
docker-compose logs -f openstack-metrics-collector | grep -i error
```

## 🔄 Mise à jour

```bash
# Pull la dernière version
git pull

# Rebuild et redémarrage
docker-compose up -d --build

# Vérifier la nouvelle version
docker-compose logs openstack-metrics-collector | grep "version"
```

## 📝 Logs

Les logs sont disponibles dans :
- **Conteneur** : `/app/logs/`
- **Host** : `./logs/` (volume monté)

Format : JSON structuré pour faciliter l'analyse.

## 🆘 Support

En cas de problème :
1. Vérifiez les logs : `docker-compose logs -f`
2. Vérifiez le healthcheck : `docker inspect openstack-metrics-collector`
3. Consultez les issues GitHub
4. Contactez le support

## 📚 Ressources

- [Documentation Docker](https://docs.docker.com/)
- [Documentation Prometheus](https://prometheus.io/docs/)
- [OpenStack SDK](https://docs.openstack.org/openstacksdk/)
