#!/usr/bin/env python3

import json
import logging
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from functools import wraps
from wsgiref.simple_server import make_server
import requests
from dotenv import load_dotenv
from openstack import connection
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, make_wsgi_app
from pythonjsonlogger import jsonlogger

def isoformat(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

# --- Logging configuration ---
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) 

# Handler fichier JSON
json_handler = logging.FileHandler('openstack-metrics.log')
json_handler.setLevel(logging.DEBUG)
json_formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
json_handler.setFormatter(json_formatter)
logger.addHandler(json_handler)

# Handler console simple
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO) 
console_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Fonction utilitaire pour nettoyer les labels Prometheus
def clean_label_value(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()

# Fonction pour Identity
def get_identity_metrics(conn, project_id):
    identity = conn.identity.get_project(project_id)
    if identity is None:
        logging.error("❌ Aucune identité trouvée")
        return None
    identity_name = identity.name
    identity_description = identity.description
    identity_domain = identity.domain_id
    identity_enabled = identity.is_enabled
    identity_id = identity.id
    identity_metrics = {
        'name': identity_name,
        'description': identity_description,
        'domain_id': identity_domain,
        'is_enabled': identity_enabled,
        'id': identity_id
    }
    logging.info("✅ Identité récupérée avec succès")
    return identity_id

# Fonction pour Compute
def list_instances(conn):
    try:
        instances = list(conn.compute.servers())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des instances")
        return None
    if not instances:
        return []
    logging.info("✅ Computes récupérées avec succès")
    return instances

# Fonction pour Images
def list_images(conn):
    try:
        images = list(conn.compute.images())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des images")
        return None
    if not images:
        return []
    logging.info("✅ Images récupérées avec succès")
    return images

# Fontion pour Block Storage
def list_snapshots(conn):
    try:
        snapshots = list(conn.block_storage.snapshots())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des snapshots")
        return None
    if not snapshots:
        return []
    logging.info("✅ Snapshots récupérées avec succès")
    return snapshots

def list_backups(conn):
    try:
        backups = list(conn.block_storage.backups())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des backups")
        return None
    if not backups:
        return []
    logging.info("✅ Backups récupérées avec succès")
    return backups

def list_volumes(conn):
    try:
        volumes = list(conn.block_storage.volumes())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des volumes")
        return None
    if not volumes:
        return []
    logging.info("✅ Volumes récupérées avec succès")
    return volumes

def list_floating_ips(conn):
    try:
        floating_ips = list(conn.network.ips())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des IP flottantes")
        return None
    if not floating_ips:
        return []
    logging.info("✅ IP flottantes récupérées avec succès")
    return floating_ips
    
def list_containers(conn):
    try:
        containers = list(conn.object_store.containers())
    except Exception:
        logging.exception("❌ Erreur lors de la récupération des containers")
        return None
    if not containers:
        return []
    logging.info("✅ Containers récupérées avec succès")
    return containers

# Fonction pour récupérer les configurations des projets
def get_project_configs():
    projects = {}
    pattern = re.compile(r'^OS_(\w+)_PROJECT(\d+)$')
    has_project_vars = any(pattern.match(key) for key in os.environ.keys())

    if has_project_vars:
        for key, value in os.environ.items():
            match = pattern.match(key)
            if match:
                var_name, project_num = match.groups()
                project_num = int(project_num)
                if project_num not in projects:
                    projects[project_num] = {}
                projects[project_num][var_name.lower()] = value
        if not projects:
            logger.warning("⚠️ Aucun projet trouvé dans les variables d’environnement avec suffixe _PROJECT.")
        # S'assurer que chaque projet a une clé 'project_id' (OpenStack UUID)
        for proj_num, conf in projects.items():
            if 'project_id' not in conf:
                conf['project_id'] = os.getenv(f"OS_PROJECT_ID_PROJECT{proj_num}", "")
    else:
        keys_needed = [
            'username', 'password', 'project_name', 'auth_url',
            'user_domain_name', 'project_domain_name'
        ]
        single_project = {}
        for key in keys_needed:
            env_key = f'OS_{key.upper()}'
            val = os.getenv(env_key)
            if val is None:
                logger.warning(f"⚠️ Variable d'environnement manquante : {env_key}")
            single_project[key] = val or ""
        single_project['project_id'] = os.getenv('OS_PROJECT_ID', '')
        projects[1] = single_project
        logger.info("ℹ️ 1 seul projet détecté")

    return projects

# Fonction pour mettre à jour les métriques
def update_metrics(metric, project_name, label_name, label_value):
    label_value_clean = clean_label_value(label_value)
    # Vérifier si la valeur du label est vide
    if label_value_clean == "":
        logging.warning(f"ℹ️ ID invalide pour la métrique {metric._name}: {label_value}")
        return
    try:
        metric.labels(project_name=project_name, **{label_name: label_value_clean}).set(1)
    except Exception:
        logging.exception(f"❌ Erreur lors de la mise à jour de la métrique {metric._name} pour {label_name}={label_value_clean}")

# Gauge Prometheus
identity_metrics = Gauge('openstack_identity_metrics', 'Metrics for OpenStack Identity service', ['project_name', 'identity_id'])
compute_metrics = Gauge('openstack_compute_metrics', 'Metrics for OpenStack Compute service', ['project_name', 'instance_id', 'flavor_id'])
image_metrics = Gauge('openstack_image_metrics', 'Metrics for OpenStack Image service', ['project_name', 'image_id'])
block_storage_metrics = Gauge('openstack_block_storage_metrics', 'Metrics for OpenStack Block Storage service', ['project_name', 'volume_id'])
network_metrics = Gauge('openstack_network_metrics', 'Metrics for OpenStack Network service', ['project_name', 'network_id'])
object_storage_metrics = Gauge('openstack_object_storage_metrics', 'Metrics for OpenStack Object Storage service', ['project_name', 'container_id'])
quota_metrics = Gauge('openstack_quota_metrics', 'OpenStack resource quotas per project', ['project_name', 'resource'])
gnocchi_metrics = Gauge('openstack_gnocchi_metric', 'Gnocchi metrics per resource', ['project_name', 'resource_id', 'metric_name'])

# Classe GnocchiAPI pour interagir avec l'API REST Gnocchi
class GnocchiAPI:
    def __init__(self, gnocchi_url, token):
        self.gnocchi_url = gnocchi_url.rstrip('/')
        self.headers = {
            "X-Auth-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_resources(self, resource_type="instance"):
        url = f"{self.gnocchi_url}/v1/resource/{resource_type}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            logger.error(f"❌ Erreur récupération ressources: {resp.status_code} {resp.text}")
            return []
        return resp.json()

    def get_metrics_for_resource(self, resource_id):
        url = f"{self.gnocchi_url}/v1/resource/instance/{resource_id}/metric"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            logger.warning(f"⚠️ Impossible de récupérer métriques pour ressource {resource_id}: {resp.status_code} {resp.text}")
            return {}
        return resp.json()

    def get_measures(self, metric_id, start_iso, end_iso):
        url = f"{self.gnocchi_url}/v1/metric/{metric_id}/measures"
        params = {
            "start": start_iso,
            "stop": end_iso,
        }
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code != 200:
            logger.warning(f"⚠️ Impossible de récupérer mesures métrique {metric_id}: {resp.status_code} {resp.text}")
            return []
        return resp.json()

# Métriques internes globales
exporter_uptime = Gauge('exporter_uptime_seconds', 'Exporter uptime in seconds')
exporter_errors = Counter('exporter_errors_total', 'Total number of exporter errors')
exporter_scrape_duration = Histogram('exporter_scrape_duration_seconds', 'Duration of exporter scrape in seconds')

# Fonction pour charger les variables d'environnement
def load_openstack_credentials():
    load_dotenv() 
    expected_vars = [
        "OS_AUTH_URL",
        "OS_PROJECT_NAME",
        "OS_USERNAME",
        "OS_PASSWORD",
        "OS_USER_DOMAIN_NAME",
    ]
    creds = {}
    missing_vars = []
    for var in expected_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            key = var.lower().replace("os_", "")
            creds[key] = value

    # Récupération du project_domain_name ou project_domain_id
    project_domain_name = os.getenv("OS_PROJECT_DOMAIN_NAME")
    project_domain_id = os.getenv("OS_PROJECT_DOMAIN_ID")
    if project_domain_name:
        creds["project_domain_name"] = project_domain_name
    elif project_domain_id:
        creds["project_domain_id"] = project_domain_id
    else:
        missing_vars.append("OS_PROJECT_DOMAIN_NAME/OS_PROJECT_DOMAIN_ID")
    if missing_vars:
        print(f"[bold red]❌ Variables OpenStack manquantes : {', '.join(missing_vars)}[/]")
        return None
    return creds

start_time = time.time()

# Collecter les métrics
def collect_project_metrics(project_config, conn_cache):
    project_name = project_config.get('project_name') or 'unknown'
    project_os_id = project_config.get('project_id') or None
    cache_key = (
        project_config['auth_url'],
        project_name,
        project_config['username'],
        project_config['user_domain_name'],
        project_config['project_domain_name'],
        os.getenv("OS_REGION_NAME", "").lower()
    )

    region = os.getenv("OS_REGION_NAME", "").lower()
    if not region:
        logger.error("❌ Variable d'environnement OS_REGION_NAME non définie.")
        exporter_errors.inc()
        return

    # Connexion OpenStack 
    conn = None
    try:
        if cache_key in conn_cache:
            conn = conn_cache[cache_key]
        else:
            conn = connection.Connection(
                auth_url=project_config['auth_url'],
                project_name=project_name,
                username=project_config['username'],
                password=project_config['password'],
                user_domain_name=project_config['user_domain_name'],
                project_domain_name=project_config['project_domain_name'],
                region_name=region
            )
            token = conn.authorize()
            if not token:
                raise Exception("Token non récupéré")
            conn_cache[cache_key] = conn
        logger.info(f"✅ Connexion réussie : {project_name} (region: {region})")
    except Exception as exc:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur de connexion OpenStack pour {project_name}")
        return

    # Récupérer les métriques pour chaque service
    try:
        identity_id = get_identity_metrics(conn, project_os_id)
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la récupération des métriques d'identité pour le projet {project_name}")
        identity_id = None

    try:
        instances = list_instances(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la récupération des instances pour le projet {project_name}")
        instances = None

    try:
        instances = list_instances(conn)
        used_image_ids = {getattr(inst.image, 'id', None) for inst in instances if hasattr(inst, 'image')}
        all_images = list_images(conn)
        images = [img for img in all_images if img.id in used_image_ids]
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la récupération des images pour le projet {project_name}")
        images = None

    try:
        volumes = list_volumes(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la récupération des volumes pour le projet {project_name}")
        volumes = None

    try:
        floating_ips = list_floating_ips(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la récupération des IP flottantes pour le projet {project_name}")
        floating_ips = None

    try:
        containers = list_containers(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la récupération des containers pour le projet {project_name}")
        containers = None

    # Identity
    update_metrics(identity_metrics, project_name, "identity_id", identity_id)

    # Compute
    if instances:
        for instance in instances:
            if instance.flavor:
                if isinstance(instance.flavor, dict):
                    flavor_id = instance.flavor.get('id', 'unknown')
                elif hasattr(instance.flavor, 'id'):
                    flavor_id = instance.flavor.id
                else:
                    flavor_id = 'unknown'
            else:
                flavor_id = 'unknown'
            # Set compute_metrics with all required labels explicitly
            compute_metrics.labels(
                project_name=project_name,
                instance_id=clean_label_value(instance.id),
                flavor_id=clean_label_value(flavor_id)
            ).set(1)

    # Images
    if images:
        for image in images:
            update_metrics(image_metrics, project_name, "image_id", image.id)

    # Block Storage
    if volumes:
        for volume in volumes:
            update_metrics(block_storage_metrics, project_name, "volume_id", volume.id)

    # Network
    if floating_ips:
        for ip in floating_ips:
            update_metrics(network_metrics, project_name, "network_id", getattr(ip, 'id', 'unknown'))

    # Object Storage
    if containers:
        for container in containers:
            update_metrics(object_storage_metrics, project_name, "container_id", getattr(container, 'id', 'unknown'))

    # Quotas
    quota_service = detect_quota_service(conn, project_os_id)
    if quota_service is None:
        exporter_errors.inc()
        logger.error(f"❌ Impossible de détecter le service quotas pour le projet {project_name}")
        quotas = None
    else:
        quotas = get_project_quotas(conn, project_os_id, service=quota_service)
        if quotas:
            allowed_quotas = {
                "cores", "ram", "instances",
                "injected_file_content_bytes", "injected_file_path_bytes", "injected_files",
                "key_pairs", "metadata_items",
                "server_group_members", "server_groups"
            }
            for resource, value in quotas.items():
                if resource not in allowed_quotas:
                    logger.debug(f"Quota ignoré (non autorisé) : {resource} = {value}")
                    continue
                quota_metrics.labels(
                    project_name=project_name,
                    resource=clean_label_value(resource)
                ).set(float(value) if value is not None else 0)

    # Gnocchi metrics
    try:
        region = os.getenv("OS_REGION_NAME", "").lower()
        REGION_TO_GNOCCHI_URL = {
            "dc3-a": "https://api.pub1.infomaniak.cloud/metric",
            "dc4-a": "https://api.pub2.infomaniak.cloud/metric",
        }
        gnocchi_url = REGION_TO_GNOCCHI_URL.get(region)

        if not gnocchi_url:
            logger.error(f"❌ Endpoint Gnocchi introuvable pour la région '{region}'. Vérifie ta variable OS_REGION_NAME.")
            return

        token = conn.session.get_token()
        gnocchi = GnocchiAPI(gnocchi_url, token)

        lookback_seconds = 300
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=lookback_seconds)
        start_iso = start.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        end_iso = end.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        resources = gnocchi.get_resources("instance")
        for res in resources:
            rid = res.get("id")
            if not rid:
                continue
            metrics = gnocchi.get_metrics_for_resource(rid)
            for metric in metrics:
                metric_id = metric.get("id")
                metric_name = metric.get("name")
                if not metric_id or not metric_name:
                    continue

                measures = gnocchi.get_measures(metric_id, start_iso, end_iso)
                if not measures:
                    continue

                last_measure = measures[-1]
                value = last_measure[2] if len(last_measure) > 2 else None
                if value is not None:
                    gnocchi_metrics.labels(
                        project_name=project_name,
                        resource_id=clean_label_value(rid),
                        metric_name=clean_label_value(metric_name)
                    ).set(float(value))
        logging.info("✅ Metrics récupérées avec succès")
    except Exception:
        exporter_errors.inc()
        logger.exception(f"❌ Erreur lors de la collecte Gnocchi pour le projet {project_name}")

def detect_quota_service(conn, project_id):
    try:
        quotas = conn.compute.get_quota_set(project_id)
        if quotas:
            return "compute"
    except Exception as e:
        logger.error("❌ Impossible de récupérer les quotas")
        return None

def get_project_quotas(conn, project_id, service="compute"):
    try:
        if service == "compute":
            quota_set = conn.compute.get_quota_set(project_id)
        elif service == "identity":
            quota_set = conn.identity.get_quota_set(project_id)
        else:
            logger.error(f"Service quotas inconnu : {service}")
            return None
        logger.info("✅ Quotas récupérés avec succès")
        return quota_set.to_dict() if hasattr(quota_set, "to_dict") else dict(quota_set)
    except Exception as e:
        logger.error(f"❌ Erreur récupération quotas pour {project_id} via {service} : {e}")
        return None

# Fonction pour la collecte des métriques (exécutée à chaque scrape) 
def collect_metrics():
    with exporter_scrape_duration.time():
        projects = get_project_configs()
        conn_cache = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for project_name, config in projects.items():
                futures.append(executor.submit(collect_project_metrics, config, conn_cache))
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    exporter_errors.inc()
                    logger.exception("❌ Erreur lors de la collecte parallèle d'un projet")
        uptime_seconds = time.time() - start_time
        exporter_uptime.set(uptime_seconds)

# CustomCollector pour déclencher la collecte à chaque scrape
class CustomCollector:
    def collect(self):
        collect_metrics()  # Met à jour toutes les métriques
        # Retourne toutes les métriques collectées
        for metric in [
            identity_metrics,
            compute_metrics,
            image_metrics,
            block_storage_metrics,
            network_metrics,
            object_storage_metrics,
            quota_metrics,
            gnocchi_metrics,
            exporter_uptime,
            exporter_errors,
            exporter_scrape_duration
        ]:
            yield from metric.collect()

# Fonction principale pour démarrer le serveur WSGI
def main():
    creds = load_openstack_credentials()
    if not creds:
        print("[bold red]❌ Impossible de charger les identifiants OpenStack. Vérifiez votre configuration.[/]")
        return

    registry = CollectorRegistry()
    registry.register(CustomCollector())
    app = make_wsgi_app(registry)
    httpd = make_server('', 8000, app)
    logger.info("📡 Exporter Prometheus démarré sur le port 8000...")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt manuel de l'exporter Prometheus.")

if __name__ == "__main__":
    main()