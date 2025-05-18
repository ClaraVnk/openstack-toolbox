#!/usr/bin/env python3

import subprocess
import sys
import importlib
import json
import requests
from datetime import datetime, timedelta
import os

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Vérifier et installer les dépendances manquantes
try:
    importlib.import_module('openstack')
except ImportError:
    print("Installation du package openstack...")
    install_package('openstacksdk')

try:
    importlib.import_module('dotenv')
except ImportError:
    print("Installation du package dotenv...")
    install_package('python-dotenv')

import openstack
from dotenv import load_dotenv

# Fonction pour afficher les en-têtes
def print_header(header):
    print("\n" + "=" * 50)
    print(header.center(50))
    print("=" * 50 + "\n")

# La spéciale Infomaniak aka gérer des version d'Openstack différentes
def check_cloudkitty_version(region='dc3-a'):
    """Vérifie si CloudKitty est disponible dans la région spécifiée"""
    region_url_map = {
        'dc3-a': 'pub1',
        'dc4-a': 'pub2'
    }
    url_region = region_url_map.get(region, 'pub1')
    base_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating"
    
    try:
        conn = openstack.connect(region_name=region)
        headers = {'X-Auth-Token': conn.session.get_token()}
        
        # Essayer différents chemins d'API
        endpoints = [
            f"{base_endpoint}",           # Racine
            f"{base_endpoint}/v1",        # v1
            f"{base_endpoint}/v2"         # v2
        ]
        
        for endpoint in endpoints:
            try:
                # Pour éviter l'erreur 405, utiliser OPTIONS au lieu de GET
                options_response = requests.options(endpoint, headers=headers)
                if options_response.status_code < 400:
                    print(f"CloudKitty est disponible sur {endpoint}")
                    return True
            except Exception as e:
                print(f"Erreur lors de la vérification de {endpoint}: {e}")
                continue
                
        print(f"CloudKitty n'est pas accessible dans la région {region}")
        return False
            
    except Exception as e:
        print(f"Erreur lors de la vérification de CloudKitty dans la région {region}: {e}")
        return False

def get_cloudkitty_version(region='dc3-a'):
    """Obtient la version de CloudKitty depuis l'API dans la région spécifiée"""
    # Mapper les noms de région aux identifiants d'URL
    region_url_map = {
        'dc3-a': 'pub1',
        'dc4-a': 'pub2'
    }
    url_region = region_url_map.get(region, 'pub1')  # Défaut à pub1 si région inconnue
    cloudkitty_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating"
    
    try:
        # Créer une connexion OpenStack pour la région spécifiée
        conn = openstack.connect(region_name=region)
        headers = {'X-Auth-Token': conn.session.get_token()}
        
        # Tentative d'obtenir les informations de version depuis l'API
        response = requests.get(f"{cloudkitty_endpoint}/v1", headers=headers)
        
        if response.status_code == 200:
            # Tentative d'extraire la version des données de réponse
            try:
                api_info = response.json()
                if 'version' in api_info:
                    version = api_info['version']
                    print(f"Version de CloudKitty détectée via API (région {region}): {version}")
                    return version
            except:
                # Fallback: au moins nous savons que c'est disponible
                print(f"CloudKitty est disponible dans la région {region} mais impossible de déterminer la version")
                return "unknown"
        else:
            print(f"Impossible d'obtenir la version de CloudKitty dans la région {region}. Code d'état: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Erreur lors de la récupération de la version de CloudKitty dans la région {region}: {e}")
        return None

def determine_cloudkitty_client_version(cloudkitty_version):
    if not cloudkitty_version:
        return None
        
    # Si la version est inconnue mais que l'API est disponible, utiliser une version récente
    if cloudkitty_version == "unknown":
        print("Version de CloudKitty inconnue, utilisation de la version 5.0.0 du client")
        return 'cloudkittyclient==5.0.0'
        
    if cloudkitty_version.startswith('13.'):
        return 'cloudkittyclient==4.1.0'
    elif cloudkitty_version.startswith('20.'):
        return 'cloudkittyclient==5.0.0'
    else:
        print(f"Version de CloudKitty non reconnue: {cloudkitty_version}")
        # Fallback sur la version la plus récente
        return 'cloudkittyclient==5.0.0'

def setup_cloudkitty(region='dc3-a'):
    """Configure la connexion à CloudKitty dans la région spécifiée"""
    # Mapper les noms de région aux identifiants d'URL
    region_url_map = {
        'dc3-a': 'pub1',
        'dc4-a': 'pub2'
    }
    url_region = region_url_map.get(region, 'pub1')  # Défaut à pub1 si région inconnue
    cloudkitty_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating"
    if not check_cloudkitty_version(region):
        return None
    
    # Obtenir la version de CloudKitty
    cloudkitty_version = get_cloudkitty_version(region)
    
    # Déterminer la version du client à installer
    client_version = determine_cloudkitty_client_version(cloudkitty_version)
    if client_version:
        print(f"Installation du client CloudKitty version: {client_version}")
        try:
            install_package(client_version)
            
            # Importer et configurer le client CloudKitty
            try:
                from cloudkittyclient.v1 import client as ck_client
                
                # Créer une connexion OpenStack pour la région spécifiée
                conn = openstack.connect(region_name=region)
                
                # Configurer CloudKitty avec l'endpoint pour la région spécifiée
                cloudkitty_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating/v1"
                cloudkitty_client = ck_client.Client(
                    session=conn.session,
                    endpoint_override=cloudkitty_endpoint
                )
                
                print(f"Client CloudKitty initialisé avec succès pour la région {region}.")
                return cloudkitty_client
                
            except ImportError as e:
                print(f"Impossible d'importer cloudkittyclient: {e}")
            except Exception as e:
                print(f"Erreur lors de la configuration du client CloudKitty pour la région {region}: {e}")
        except Exception as e:
            print(f"Erreur lors de l'installation du client CloudKitty: {e}")
    
    return None

def get_all_regions_cloudkitty():
    """Tente de configurer CloudKitty pour toutes les régions disponibles et retourne le premier client fonctionnel"""
    regions = ['dc3-a', 'dc4-a']
    
    for region in regions:
        print(f"\nTentative de configuration de CloudKitty pour la région {region}...")
        client = setup_cloudkitty(region)
        if client:
            print(f"Configuration réussie pour la région {region}")
            return client, region
    
    print("Impossible de configurer CloudKitty pour aucune région")
    return None, None

def get_billing_data(start_time, end_time):
    # Commande pour récupérer les données de facturation
    command = [
        "openstack", "rating", "dataframes", "get",
        "-b", start_time,
        "-e", end_time,
        "-c", "Resources",
        "-f", "json"
    ]

    # Exécuter la commande et récupérer la sortie
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("Erreur lors de la récupération des données de facturation")
        print(result.stderr)
        return None

    return json.loads(result.stdout)

def calculate_instance_cost(billing_data, icu_to_chf=50, icu_to_euro=55.5):
    if not billing_data:
        return 0.0, 0.0  # Retourne zéro pour les deux devises si pas de données

    total_icu = 0
    for entry in billing_data:
        # Additionner tous les ICUs
        total_icu += entry.get('rating', {}).get('price', 0)
    
    # Convertir en CHF et EUR
    cost_chf = total_icu / icu_to_chf
    cost_euro = total_icu / icu_to_euro
    
    return cost_chf, cost_euro

def format_size(size_bytes):
    # Définir les unités et leurs seuils
    units = [
        ('To', 1000000000000),
        ('Go', 1000000000),
        ('Mo', 1000000),
        ('Ko', 1000)
    ]

    # Parcourir les unités pour trouver la plus appropriée
    for unit, threshold in units:
        if size_bytes >= threshold:
            size = size_bytes / threshold
            return f"{size:.2f} {unit}"
    return f"{size_bytes} octets"

# Lister les images privées et partagées
def list_images(conn):
    print_header("LISTE DES IMAGES UTILISEES")
    # Récupérer les images privées et les convertir en liste
    private_images = list(conn.image.images(visibility='private'))
    # Récupérer les images partagées et les convertir en liste
    shared_images = list(conn.image.images(visibility='shared'))
    # Combiner les images privées et partagées
    all_images = private_images + shared_images

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<36} {'Visibilité':<20}")
    print("-" * 96) 
    for image in all_images:
        print(f"{image.id:<36} {image.name:<36} {image.visibility:<20}")

# Lister les instances
def list_instances(conn, cloudkitty=None):
    print_header("LISTE DES INSTANCES")
    # Récupérer les instances
    instances = list(conn.compute.servers())
    # Taux de conversion ICU vers monnaies
    icu_to_chf = 50  # Taux de conversion ICU vers CHF
    icu_to_euro = 55.5  # Taux de conversion ICU vers EUR
    # Récupérer toutes les flavors disponibles
    flavors = {flavor.id: flavor for flavor in conn.compute.flavors()}

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Flavor ID':<20} {'Uptime':<20} {'Coût (CHF)':<12} {'Coût (EUR)':<12}")
    print("-" * 130)
    
    # Définir la période pour les données de facturation (30 derniers jours)
    start_time = datetime.now() - timedelta(days=30)

    for instance in instances:
        flavor_id = instance.flavor['id']
        # Convertir la date de création en objet datetime
        created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
        # Calculer l'uptime
        uptime = datetime.now() - created_at
        # Formater l'uptime en jours, heures, minutes, secondes
        uptime_str = str(uptime).split('.')[0]  # Supprimer les microsecondes
        
        # Récupérer les données de billing si CloudKitty est disponible
        billing_data = None
        try:
            # Utiliser le client passé en paramètre s'il existe
            if cloudkitty:
                billing_data = cloudkitty.report.get_dataframes(
                    begin=start_time.isoformat(),
                    end=datetime.now().isoformat(),
                    resource_id=instance.id
                )
        except Exception as e:
            # Gérer silencieusement l'erreur ou afficher un message informatif
            pass
        
        # Calculer le coût en CHF et EUR
        cost_chf, cost_euro = calculate_instance_cost(billing_data, icu_to_chf, icu_to_euro)
        print(f"{instance.id:<36} {instance.name:<20} {flavor_id:<20} {uptime_str:<20} {cost_chf:.2f} CHF {cost_euro:.2f} EUR")

# Lister les snapshots
def list_snapshots(conn):
    print_header("LISTE DES SNAPSHOTS")
    # Récupérer les snapshots
    snapshots = list(conn.block_storage.snapshots())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Volume associé':<20}")
    print("-" * 96)
    for snapshot in snapshots:
        print(f"{snapshot.id:<36} {snapshot.name:<20} {snapshot.volume_id:<20}")

# Lister les backups
def list_backups(conn):
    print_header("LISTE DES BACKUPS")
    # Récupérer les backups
    backups = list(conn.block_storage.backups())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Volume associé':<20}")
    print("-" * 96)
    for backup in backups:
        print(f"{backup.id:<36} {backup.name:<20} {backup.volume_id:<20}")

# Lister les volumes 
def list_volumes(conn):
    print_header("LISTE DES VOLUMES")
    # Récupérer les volumes
    volumes = list(conn.block_storage.volumes())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Taille (Go)':<20} {'Type':<20} {'Attaché':<20} {'Snapshot associé':<20}")
    print("-" * 116)
    for volume in volumes:
        attached = "Oui" if volume.attachments else "Non"
        # Remplacer None par une chaîne vide pour snapshot_id
        snapshot_id = volume.snapshot_id if volume.snapshot_id else 'Aucun'
        print(f"{volume.id:<36} {volume.name:<20} {volume.size:<20} {volume.volume_type:<20} {attached:<20} {snapshot_id:<20}")

# Récupérer les volumes attachés aux instances
def mounted_volumes(conn):
    instances = conn.compute.servers()
    volumes = conn.block_storage.volumes()
    instance_volumes = {}

    for volume in volumes:
        if volume.attachments:
            for attachment in volume.attachments:
                instance_id = attachment['server_id']
                if instance_id not in instance_volumes:
                    instance_volumes[instance_id] = []
                instance_volumes[instance_id].append(volume)

    tree = {}
    for instance in instances:
        instance_id = instance.id
        instance_name = instance.name
        if instance_id in instance_volumes:
            tree[instance_name] = [volume.name for volume in instance_volumes[instance_id]]
        else:
            tree[instance_name] = []

    return tree

# Afficher l'arborescence
def print_tree(tree):
    for instance, volumes in tree.items():
        print(f"Instance: {instance}")
        for volume in volumes:
            print(f"  Volume: {volume}")

# Lister les IP flottantes
def list_floating_ips(conn):
    print_header("LISTE DES FLOATING IPs")
    # Récupérer les adresses IP flottantes
    floating_ips = list(conn.network.ips())

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'IP':<20} {'Statut':<20}")
    print("-" * 96)
    for ip in floating_ips:
        print(f"{ip.id:<36} {ip.floating_ip_address:<20} {ip.status:<20}")

# Lister les containers
def list_containers(conn):
    print_header("LISTE DES CONTAINERS")
    # Récupérer les containers
    containers = list(conn.object_store.containers())

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<20} {'Taille totale':<20}")
    print("-" * 40)
    for container in containers:
        size_formatted = format_size(container.bytes)
        print(f"{container.name:<20} {size_formatted:<20}")

def main():
    # Se connecter à OpenStack
    load_dotenv()
    
    auth_url = os.getenv("OS_AUTH_URL")
    project_name = os.getenv("OS_PROJECT_NAME")
    username = os.getenv("OS_USERNAME")
    password = os.getenv("OS_PASSWORD")
    user_domain_name = os.getenv("OS_USER_DOMAIN_NAME")
    project_domain_name = os.getenv("OS_PROJECT_DOMAIN_NAME")
    
    # Créer la connexion OpenStack
    conn = openstack.connect(
        auth_url=auth_url,
        project_name=project_name,
        username=username,
        password=password,
        user_domain_name=user_domain_name,
        project_domain_name=project_domain_name,
    )
    
    # Vérifier la connexion
    if not conn.authorize():
        print("Échec de la connexion à OpenStack")
        return
    
    print("Connexion réussie à OpenStack")
    
    # Configurer CloudKitty
    cloudkitty, region = get_all_regions_cloudkitty()
    if cloudkitty:
        print(f"CloudKitty est prêt à être utilisé dans la région {region}.")
    else:
        print("Impossible de configurer CloudKitty pour aucune région.")
    
    # Lister les ressources
    list_images(conn)
    list_instances(conn, cloudkitty)
    list_snapshots(conn)
    list_backups(conn)
    list_volumes(conn)
    
    print_header("ARBORESCENCE DES VOLUMES")
    tree = mounted_volumes(conn)
    print_tree(tree)
    
    list_floating_ips(conn)
    list_containers(conn)

if __name__ == "__main__":
    main()
