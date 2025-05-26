#!/usr/bin/env python3

import logging
import os
import re
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
from src.config import get_language_preference
from src.utils import isoformat, parse_flavor_name

# Dictionnaire des traductions
TRANSLATIONS = {
    "fr": {
        "no_identity": "❌ Aucune identité trouvée",
        "identity_success": "✅ Identité récupérée avec succès",
        "instances_error": "❌ Erreur lors de la récupération des instances",
        "instances_success": "✅ Computes récupérées avec succès",
        "images_error": "❌ Erreur lors de la récupération des images",
        "images_success": "✅ Images récupérées avec succès",
        "snapshots_error": "❌ Erreur lors de la récupération des snapshots",
        "snapshots_success": "✅ Snapshots récupérées avec succès",
        "backups_error": "❌ Erreur lors de la récupération des backups",
        "backups_success": "✅ Backups récupérées avec succès",
        "volumes_error": "❌ Erreur lors de la récupération des volumes",
        "volumes_success": "✅ Volumes récupérées avec succès",
        "floating_ips_error": "❌ Erreur lors de la récupération des IP flottantes",
        "floating_ips_success": "✅ IP flottantes récupérées avec succès",
        "containers_error": "❌ Erreur lors de la récupération des containers",
        "containers_success": "✅ Containers récupérées avec succès",
        "no_project_vars": "⚠️ Aucun projet trouvé dans les variables d'environnement avec suffixe _PROJECT.",
        "missing_env_var": "⚠️ Variable d'environnement manquante : {}",
        "single_project": "ℹ️ 1 seul projet détecté",
        "invalid_metric_id": "ℹ️ ID invalide pour la métrique {}: {}",
        "metric_update_error": "❌ Erreur lors de la mise à jour de la métrique {} pour {}={}",
        "resources_error": "❌ Erreur récupération ressources: {} {}",
        "metrics_resource_error": "⚠️ Impossible de récupérer métriques pour ressource {}: {} {}",
        "measures_error": "⚠️ Impossible de récupérer mesures métrique {}: {} {}",
        "missing_vars": "❌ Variables OpenStack manquantes : {}",
        "region_undefined": "❌ Variable d'environnement OS_REGION_NAME non définie.",
        "token_error": "Token non récupéré",
        "connection_success": "✅ Connexion réussie : {} (region: {})",
        "connection_error": "❌ Erreur de connexion OpenStack pour {}",
        "identity_metrics_error": "❌ Erreur lors de la récupération des métriques d'identité pour le projet {}",
        "instances_project_error": "❌ Erreur lors de la récupération des instances pour le projet {}",
        "images_project_error": "❌ Erreur lors de la récupération des images pour le projet {}",
        "volumes_project_error": "❌ Erreur lors de la récupération des volumes pour le projet {}",
        "floating_ips_project_error": "❌ Erreur lors de la récupération des IP flottantes pour le projet {}",
        "containers_project_error": "❌ Erreur lors de la récupération des containers pour le projet {}",
        "quotas_service_error": "❌ Impossible de détecter le service quotas pour le projet {}",
        "quota_ignored": "Quota ignoré (non autorisé) : {} = {}",
        "gnocchi_endpoint_error": "❌ Endpoint Gnocchi introuvable pour la région '{}'. Vérifie ta variable OS_REGION_NAME.",
        "metrics_success": "✅ Metrics récupérées avec succès",
        "gnocchi_error": "❌ Erreur lors de la collecte Gnocchi pour le projet {}",
        "quotas_error": "❌ Impossible de récupérer les quotas",
        "unknown_quota_service": "Service quotas inconnu : {}",
        "quotas_success": "✅ Quotas récupérés avec succès",
        "quota_error": "❌ Erreur récupération quotas pour {} via {} : {}",
        "parallel_error": "❌ Erreur lors de la collecte parallèle d'un projet",
        "credentials_error": "❌ Impossible de charger les identifiants OpenStack. Vérifiez votre configuration.",
        "exporter_started": "📡 Exporter Prometheus démarré sur le port 8000...",
        "manual_stop": "🛑 Arrêt manuel de l'exporter Prometheus.",
        "identity_metrics_desc": "Métriques du service d'identité OpenStack",
        "compute_metrics_desc": "Métriques du service de calcul OpenStack",
        "image_metrics_desc": "Métriques du service d'images OpenStack",
        "block_storage_metrics_desc": "Métriques du service de stockage en bloc OpenStack",
        "network_metrics_desc": "Métriques du service réseau OpenStack",
        "object_storage_metrics_desc": "Métriques du service de stockage d'objets OpenStack",
        "quota_metrics_desc": "Quotas de ressources OpenStack par projet",
        "gnocchi_metrics_desc": "Métriques Gnocchi par ressource",
        "exporter_uptime_desc": "Temps de fonctionnement de l'exporteur en secondes",
        "exporter_errors_desc": "Nombre total d'erreurs de l'exporteur",
        "exporter_scrape_desc": "Durée de la collecte des métriques en secondes",
        "log_format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        "console_log_format": "%(asctime)s %(levelname)s: %(message)s",
        "log_file": "openstack-metrics.log",
        "unknown": "inconnu",
        "date_format": "%H:%M:%S",
        "metric_name": "nom",
        "metric_description": "description",
        "metric_domain_id": "domaine_id",
        "metric_enabled": "actif",
        "metric_id": "id"
    },
    "en": {
        "no_identity": "❌ No identity found",
        "identity_success": "✅ Identity retrieved successfully",
        "instances_error": "❌ Error retrieving instances",
        "instances_success": "✅ Computes retrieved successfully",
        "images_error": "❌ Error retrieving images",
        "images_success": "✅ Images retrieved successfully",
        "snapshots_error": "❌ Error retrieving snapshots",
        "snapshots_success": "✅ Snapshots retrieved successfully",
        "backups_error": "❌ Error retrieving backups",
        "backups_success": "✅ Backups retrieved successfully",
        "volumes_error": "❌ Error retrieving volumes",
        "volumes_success": "✅ Volumes retrieved successfully",
        "floating_ips_error": "❌ Error retrieving floating IPs",
        "floating_ips_success": "✅ Floating IPs retrieved successfully",
        "containers_error": "❌ Error retrieving containers",
        "containers_success": "✅ Containers retrieved successfully",
        "no_project_vars": "⚠️ No projects found in environment variables with _PROJECT suffix.",
        "missing_env_var": "⚠️ Missing environment variable: {}",
        "single_project": "ℹ️ 1 single project detected",
        "invalid_metric_id": "ℹ️ Invalid ID for metric {}: {}",
        "metric_update_error": "❌ Error updating metric {} for {}={}",
        "resources_error": "❌ Error retrieving resources: {} {}",
        "metrics_resource_error": "⚠️ Unable to retrieve metrics for resource {}: {} {}",
        "measures_error": "⚠️ Unable to retrieve measures for metric {}: {} {}",
        "missing_vars": "❌ Missing OpenStack variables: {}",
        "region_undefined": "❌ OS_REGION_NAME environment variable not defined.",
        "token_error": "Token not retrieved",
        "connection_success": "✅ Connection successful: {} (region: {})",
        "connection_error": "❌ OpenStack connection error for {}",
        "identity_metrics_error": "❌ Error retrieving identity metrics for project {}",
        "instances_project_error": "❌ Error retrieving instances for project {}",
        "images_project_error": "❌ Error retrieving images for project {}",
        "volumes_project_error": "❌ Error retrieving volumes for project {}",
        "floating_ips_project_error": "❌ Error retrieving floating IPs for project {}",
        "containers_project_error": "❌ Error retrieving containers for project {}",
        "quotas_service_error": "❌ Unable to detect quota service for project {}",
        "quota_ignored": "Quota ignored (not allowed): {} = {}",
        "gnocchi_endpoint_error": "❌ Gnocchi endpoint not found for region '{}'. Check your OS_REGION_NAME variable.",
        "metrics_success": "✅ Metrics retrieved successfully",
        "gnocchi_error": "❌ Error during Gnocchi collection for project {}",
        "quotas_error": "❌ Unable to retrieve quotas",
        "unknown_quota_service": "Unknown quota service: {}",
        "quotas_success": "✅ Quotas retrieved successfully",
        "quota_error": "❌ Error retrieving quotas for {} via {}: {}",
        "parallel_error": "❌ Error during parallel project collection",
        "credentials_error": "❌ Unable to load OpenStack credentials. Please check your configuration.",
        "exporter_started": "📡 Prometheus exporter started on port 8000...",
        "manual_stop": "🛑 Manual stop of Prometheus exporter.",
        "identity_metrics_desc": "Metrics for OpenStack Identity service",
        "compute_metrics_desc": "Metrics for OpenStack Compute service",
        "image_metrics_desc": "Metrics for OpenStack Image service",
        "block_storage_metrics_desc": "Metrics for OpenStack Block Storage service",
        "network_metrics_desc": "Metrics for OpenStack Network service",
        "object_storage_metrics_desc": "Metrics for OpenStack Object Storage service",
        "quota_metrics_desc": "OpenStack resource quotas per project",
        "gnocchi_metrics_desc": "Gnocchi metrics per resource",
        "exporter_uptime_desc": "Exporter uptime in seconds",
        "exporter_errors_desc": "Total number of exporter errors",
        "exporter_scrape_desc": "Duration of exporter scrape in seconds",
        "log_format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        "console_log_format": "%(asctime)s %(levelname)s: %(message)s",
        "log_file": "openstack-metrics.log",
        "unknown": "unknown",
        "date_format": "%H:%M:%S",
        "metric_name": "name",
        "metric_description": "description",
        "metric_domain_id": "domain_id",
        "metric_enabled": "enabled",
        "metric_id": "id"
    }
}

def isoformat(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

# --- Logging configuration ---
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) 

# Handler fichier JSON
lang = get_language_preference()
json_handler = logging.FileHandler(TRANSLATIONS[lang]["log_file"])
json_handler.setLevel(logging.DEBUG)
json_formatter = jsonlogger.JsonFormatter(TRANSLATIONS[lang]["log_format"])
json_handler.setFormatter(json_formatter)
logger.addHandler(json_handler)

# Handler console simple
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO) 
console_formatter = logging.Formatter(TRANSLATIONS[lang]["console_log_format"], datefmt=TRANSLATIONS[lang]["date_format"])
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Fonction utilitaire pour nettoyer les labels Prometheus
def clean_label_value(value):
    """
    Nettoie une valeur pour l'utiliser comme label Prometheus.
    
    Args:
        value (Any): Valeur à nettoyer (peut être None)
        
    Returns:
        str: Valeur nettoyée et convertie en chaîne
        
    Examples:
        >>> clean_label_value("my-label")
        'my-label'
        >>> clean_label_value(None)
        ''
        >>> clean_label_value(123)
        '123'
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()

# Fonction pour Identity
def get_identity_metrics(conn, project_id):
    lang = get_language_preference()
    identity = conn.identity.get_project(project_id)
    if identity is None:
        logging.error(TRANSLATIONS[lang]["no_identity"])
        return None
    logging.info(TRANSLATIONS[lang]["identity_success"])
    return identity.id

# Fonction pour Compute
def list_instances(conn):
    lang = get_language_preference()
    try:
        instances = list(conn.compute.servers())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["instances_error"])
        return None
    if not instances:
        return []
    logging.info(TRANSLATIONS[lang]["instances_success"])
    return instances

# Fonction pour Images
def list_images(conn):
    lang = get_language_preference()
    try:
        images = list(conn.compute.images())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["images_error"])
        return None
    if not images:
        return []
    logging.info(TRANSLATIONS[lang]["images_success"])
    return images

# Fonction pour Block Storage
def list_snapshots(conn):
    lang = get_language_preference()
    try:
        snapshots = list(conn.block_storage.snapshots())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["snapshots_error"])
        return None
    if not snapshots:
        return []
    logging.info(TRANSLATIONS[lang]["snapshots_success"])
    return snapshots

def list_backups(conn):
    lang = get_language_preference()
    try:
        backups = list(conn.block_storage.backups())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["backups_error"])
        return None
    if not backups:
        return []
    logging.info(TRANSLATIONS[lang]["backups_success"])
    return backups

def list_volumes(conn):
    lang = get_language_preference()
    try:
        volumes = list(conn.block_storage.volumes())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["volumes_error"])
        return None
    if not volumes:
        return []
    logging.info(TRANSLATIONS[lang]["volumes_success"])
    return volumes

def list_floating_ips(conn):
    lang = get_language_preference()
    try:
        floating_ips = list(conn.network.ips())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["floating_ips_error"])
        return None
    if not floating_ips:
        return []
    logging.info(TRANSLATIONS[lang]["floating_ips_success"])
    return floating_ips
    
def list_containers(conn):
    lang = get_language_preference()
    try:
        containers = list(conn.object_store.containers())
    except Exception:
        logging.exception(TRANSLATIONS[lang]["containers_error"])
        return None
    if not containers:
        return []
    logging.info(TRANSLATIONS[lang]["containers_success"])
    return containers

# Fonction pour récupérer les configurations des projets
def get_project_configs():
    lang = get_language_preference()
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
            logger.warning(TRANSLATIONS[lang]["no_project_vars"])
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
                logger.warning(TRANSLATIONS[lang]["missing_env_var"].format(env_key))
            single_project[key] = val or ""
        single_project['project_id'] = os.getenv('OS_PROJECT_ID', '')
        projects[1] = single_project
        logger.info(TRANSLATIONS[lang]["single_project"])

    return projects

# Fonction pour mettre à jour les métriques
def update_metrics(metric, project_name, label_name, label_value):
    lang = get_language_preference()
    label_value_clean = clean_label_value(label_value)
    # Vérifier si la valeur du label est vide
    if label_value_clean == "":
        logging.warning(TRANSLATIONS[lang]["invalid_metric_id"].format(metric._name, label_value))
        return
    try:
        metric.labels(project_name=project_name, **{label_name: label_value_clean}).set(1)
    except Exception:
        logging.exception(TRANSLATIONS[lang]["metric_update_error"].format(metric._name, label_name, label_value_clean))

# Gauge Prometheus
identity_metrics = Gauge('openstack_identity_metrics', TRANSLATIONS[lang]["identity_metrics_desc"], ['project_name', 'identity_id'])
compute_metrics = Gauge('openstack_compute_metrics', TRANSLATIONS[lang]["compute_metrics_desc"], ['project_name', 'instance_id', 'flavor_id'])
image_metrics = Gauge('openstack_image_metrics', TRANSLATIONS[lang]["image_metrics_desc"], ['project_name', 'image_id'])
block_storage_metrics = Gauge('openstack_block_storage_metrics', TRANSLATIONS[lang]["block_storage_metrics_desc"], ['project_name', 'volume_id'])
network_metrics = Gauge('openstack_network_metrics', TRANSLATIONS[lang]["network_metrics_desc"], ['project_name', 'network_id'])
object_storage_metrics = Gauge('openstack_object_storage_metrics', TRANSLATIONS[lang]["object_storage_metrics_desc"], ['project_name', 'container_id'])
quota_metrics = Gauge('openstack_quota_metrics', TRANSLATIONS[lang]["quota_metrics_desc"], ['project_name', 'resource'])
gnocchi_metrics = Gauge('openstack_gnocchi_metric', TRANSLATIONS[lang]["gnocchi_metrics_desc"], ['project_name', 'resource_id', 'metric_name'])

# Classe GnocchiAPI pour interagir avec l'API REST Gnocchi
class GnocchiAPI:
    """
    Client API pour interagir avec Gnocchi, le service de métriques d'OpenStack.
    
    Args:
        gnocchi_url (str): URL de base de l'API Gnocchi
        token (str): Token d'authentification OpenStack
        
    Examples:
        >>> conn = connection.Connection(**creds)
        >>> token = conn.session.get_token()
        >>> gnocchi = GnocchiAPI("https://gnocchi.example.com", token)
        >>> resources = gnocchi.get_resources("instance")
    """
    
    def __init__(self, gnocchi_url, token):
        self.gnocchi_url = gnocchi_url.rstrip('/')
        self.headers = {
            "X-Auth-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_resources(self, resource_type="instance"):
        """
        Récupère la liste des ressources d'un type donné.
        
        Args:
            resource_type (str): Type de ressource (default: "instance")
            
        Returns:
            list: Liste des ressources trouvées
            
        Examples:
            >>> resources = gnocchi.get_resources("instance")
            >>> for res in resources:
            ...     print(f"ID: {res['id']}, Name: {res.get('name')}")
        """
        lang = get_language_preference()
        url = f"{self.gnocchi_url}/v1/resource/{resource_type}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            logger.error(TRANSLATIONS[lang]["resources_error"].format(resp.status_code, resp.text))
            return []
        return resp.json()

    def get_metrics_for_resource(self, resource_id):
        """
        Récupère les métriques associées à une ressource.
        
        Args:
            resource_id (str): ID de la ressource
            
        Returns:
            dict: Dictionnaire des métriques de la ressource
            
        Examples:
            >>> metrics = gnocchi.get_metrics_for_resource("instance-id-123")
            >>> for metric in metrics:
            ...     print(f"Metric: {metric['name']}, ID: {metric['id']}")
        """
        lang = get_language_preference()
        url = f"{self.gnocchi_url}/v1/resource/instance/{resource_id}/metric"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            logger.warning(TRANSLATIONS[lang]["metrics_resource_error"].format(resource_id, resp.status_code, resp.text))
            return {}
        return resp.json()

    def get_measures(self, metric_id, start_iso, end_iso):
        """
        Récupère les mesures d'une métrique sur une période donnée.
        
        Args:
            metric_id (str): ID de la métrique
            start_iso (str): Date de début au format ISO 8601
            end_iso (str): Date de fin au format ISO 8601
            
        Returns:
            list: Liste des mesures [(timestamp, value, granularity), ...]
            
        Examples:
            >>> start = "2024-03-15T00:00:00+00:00"
            >>> end = "2024-03-15T23:59:59+00:00"
            >>> measures = gnocchi.get_measures("metric-id-123", start, end)
            >>> for ts, val, gran in measures:
            ...     print(f"Time: {ts}, Value: {val}")
        """
        lang = get_language_preference()
        url = f"{self.gnocchi_url}/v1/metric/{metric_id}/measures"
        params = {
            "start": start_iso,
            "stop": end_iso,
        }
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code != 200:
            logger.warning(TRANSLATIONS[lang]["measures_error"].format(metric_id, resp.status_code, resp.text))
            return []
        return resp.json()

def collect_resource_metrics(gnocchi, rid, start_iso, end_iso):
    """
    Collecte les métriques pour une ressource spécifique.
    
    Args:
        gnocchi (GnocchiAPI): Instance du client Gnocchi
        rid (str): ID de la ressource
        start_iso (str): Date de début au format ISO 8601
        end_iso (str): Date de fin au format ISO 8601
        
    Returns:
        list: Liste de tuples (resource_id, metric_name, value)
        
    Examples:
        >>> metrics = collect_resource_metrics(gnocchi, "instance-id-123",
        ...     "2024-03-15T00:00:00+00:00",
        ...     "2024-03-15T23:59:59+00:00")
        >>> for rid, name, value in metrics:
        ...     print(f"Resource: {rid}, Metric: {name}, Value: {value}")
    """
    metrics = gnocchi.get_metrics_for_resource(rid)
    results = []
    for metric in metrics:
        metric_id = metric.get("id")
        metric_name = metric.get("name")
        if not metric_id or not metric_name:
            continue
        measures = gnocchi.get_measures(metric_id, start_iso, end_iso)
        if measures:
            results.append((rid, metric_name, measures[-1][2]))
    return results

def collect_gnocchi_metrics_parallel(gnocchi, resources, start_iso, end_iso, project_name):
    """
    Collecte les métriques Gnocchi en parallèle pour toutes les ressources.
    
    Args:
        gnocchi (GnocchiAPI): Instance du client Gnocchi
        resources (list): Liste des ressources à traiter
        start_iso (str): Date de début au format ISO 8601
        end_iso (str): Date de fin au format ISO 8601
        project_name (str): Nom du projet OpenStack
        
    Examples:
        >>> collect_gnocchi_metrics_parallel(gnocchi, resources,
        ...     "2024-03-15T00:00:00+00:00",
        ...     "2024-03-15T23:59:59+00:00",
        ...     "my-project")
    """
    lang = get_language_preference()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for res in resources:
            rid = res.get("id")
            if rid:
                futures.append(executor.submit(collect_resource_metrics, gnocchi, rid, start_iso, end_iso))
        
        for future in as_completed(futures):
            try:
                metrics = future.result()
                for rid, metric_name, value in metrics:
                    if value is not None:
                        gnocchi_metrics.labels(
                            project_name=project_name,
                            resource_id=clean_label_value(rid),
                            metric_name=clean_label_value(metric_name)
                        ).set(float(value))
            except Exception as e:
                logger.exception(f"Error collecting Gnocchi metrics: {e}")
                exporter_errors.inc()

# Métriques internes globales
exporter_uptime = Gauge('exporter_uptime_seconds', TRANSLATIONS[lang]["exporter_uptime_desc"])
exporter_errors = Counter('exporter_errors_total', TRANSLATIONS[lang]["exporter_errors_desc"])
exporter_scrape_duration = Histogram('exporter_scrape_duration_seconds', TRANSLATIONS[lang]["exporter_scrape_desc"])

# Fonction pour charger les variables d'environnement
def load_openstack_credentials():
    lang = get_language_preference()
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
        print(f"[bold red]{TRANSLATIONS[lang]['missing_vars'].format(', '.join(missing_vars))}[/]")
        return None
    return creds

start_time = time.time()

# Collecter les métrics
def collect_project_metrics(project_config, conn_cache):
    lang = get_language_preference()
    project_name = project_config.get('project_name') or TRANSLATIONS[lang]["unknown"]
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
        logger.error(TRANSLATIONS[lang]["region_undefined"])
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
                raise Exception(TRANSLATIONS[lang]["token_error"])
            conn_cache[cache_key] = conn
        logger.info(TRANSLATIONS[lang]["connection_success"].format(project_name, region))
    except Exception as exc:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["connection_error"].format(project_name))
        return

    # Récupérer les métriques pour chaque service
    try:
        identity_id = get_identity_metrics(conn, project_os_id)
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["identity_metrics_error"].format(project_name))
        identity_id = None

    try:
        instances = list_instances(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["instances_project_error"].format(project_name))
        instances = None

    try:
        if instances:
            used_image_ids = {getattr(inst.image, 'id', None) for inst in instances if hasattr(inst, 'image')}
            all_images = list_images(conn)
            images = [img for img in all_images if img.id in used_image_ids]
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["images_project_error"].format(project_name))
        instances = None
        images = None

    try:
        volumes = list_volumes(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["volumes_project_error"].format(project_name))
        volumes = None

    try:
        floating_ips = list_floating_ips(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["floating_ips_project_error"].format(project_name))
        floating_ips = None

    try:
        containers = list_containers(conn)
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["containers_project_error"].format(project_name))
        containers = None

    # Identity
    update_metrics(identity_metrics, project_name, "identity_id", identity_id)

    # Compute
    if instances:
        for instance in instances:
            if instance.flavor:
                if isinstance(instance.flavor, dict):
                    flavor_id = instance.flavor.get('id', TRANSLATIONS[lang]["unknown"])
                elif hasattr(instance.flavor, 'id'):
                    flavor_id = instance.flavor.id
                else:
                    flavor_id = TRANSLATIONS[lang]["unknown"]
            else:
                flavor_id = TRANSLATIONS[lang]["unknown"]
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
            update_metrics(network_metrics, project_name, "network_id", getattr(ip, 'id', TRANSLATIONS[lang]["unknown"]))

    # Object Storage
    if containers:
        for container in containers:
            update_metrics(object_storage_metrics, project_name, "container_id", getattr(container, 'id', TRANSLATIONS[lang]["unknown"]))

    # Quotas
    quota_service = detect_quota_service(conn, project_os_id)
    if quota_service is None:
        exporter_errors.inc()
        logger.error(TRANSLATIONS[lang]["quotas_service_error"].format(project_name))
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
                    logger.debug(TRANSLATIONS[lang]["quota_ignored"].format(resource, value))
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
            logger.error(TRANSLATIONS[lang]["gnocchi_endpoint_error"].format(region))
            return

        token = conn.session.get_token()
        gnocchi = GnocchiAPI(gnocchi_url, token)

        lookback_seconds = 300
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=lookback_seconds)
        start_iso = start.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        end_iso = end.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        resources = gnocchi.get_resources("instance")
        collect_gnocchi_metrics_parallel(gnocchi, resources, start_iso, end_iso, project_name)
        
        logging.info(TRANSLATIONS[lang]["metrics_success"])
    except Exception:
        exporter_errors.inc()
        logger.exception(TRANSLATIONS[lang]["gnocchi_error"].format(project_name))

def detect_quota_service(conn, project_id):
    lang = get_language_preference()
    try:
        quotas = conn.compute.get_quota_set(project_id)
        if quotas:
            return "compute"
    except Exception as e:
        logger.error(TRANSLATIONS[lang]["quotas_error"])
        return None

def get_project_quotas(conn, project_id, service="compute"):
    lang = get_language_preference()
    try:
        if service == "compute":
            quota_set = conn.compute.get_quota_set(project_id)
        elif service == "identity":
            quota_set = conn.identity.get_quota_set(project_id)
        else:
            logger.error(TRANSLATIONS[lang]["unknown_quota_service"].format(service))
            return None
        logger.info(TRANSLATIONS[lang]["quotas_success"])
        return quota_set.to_dict() if hasattr(quota_set, "to_dict") else dict(quota_set)
    except Exception as e:
        logger.error(TRANSLATIONS[lang]["quota_error"].format(project_id, service, e))
        return None

# Fonction pour la collecte des métriques (exécutée à chaque scrape) 
def collect_metrics():
    lang = get_language_preference()
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
                    logger.exception(TRANSLATIONS[lang]["parallel_error"])
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
    lang = get_language_preference()
    creds = load_openstack_credentials()
    if not creds:
        print(f"[bold red]{TRANSLATIONS[lang]['credentials_error']}[/]")
        return

    registry = CollectorRegistry()
    registry.register(CustomCollector())
    app = make_wsgi_app(registry)
    httpd = make_server('', 8000, app)
    logger.info(TRANSLATIONS[lang]["exporter_started"])

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info(TRANSLATIONS[lang]["manual_stop"])

if __name__ == "__main__":
    main()