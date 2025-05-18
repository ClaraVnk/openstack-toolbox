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

# Fonction pour convertir nom de région en identifiant URL
def region_to_url_id(region):
    """Convertit un nom de région en identifiant d'URL"""
    region_url_map = {
        'dc3-a': 'pub1',
        'dc4-a': 'pub2'
    }
    return region_url_map.get(region, 'pub1')  # Défaut à pub1 si région inconnue

# La spéciale Infomaniak aka gérer des version d'Openstack différentes
def check_cloudkitty_version(region='dc3-a'):
    """Vérifie si CloudKitty est disponible dans la région spécifiée"""
    url_region = region_to_url_id(region)
    cloudkitty_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating"
    
    try:
        # Créer une connexion OpenStack pour la région spécifiée
        conn = openstack.connect(region_name=region)
        
        # Utiliser le token d'authentification pour la requête
        headers = {'X-Auth-Token': conn.session.get_token()}
        
        # Vérifier si l'endpoint est accessible
        response = requests.get(f"{cloudkitty_endpoint}/v1", headers=headers)
        
        if response.status_code == 200:
            print(f"CloudKitty est disponible sur Infomaniak OpenStack (région {region}).")
            return True
        else:
            print(f"CloudKitty n'est pas accessible dans la région {region}. Code d'état: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Erreur lors de la vérification de CloudKitty dans la région {region}: {e}")
        return False

def get_cloudkitty_version(region='dc3-a'):
    """Obtient la version de CloudKitty depuis l'API dans la région spécifiée"""
    url_region = region_to_url_id(region)
    cloudkitty_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating"
    
    try:
        # Créer une connexion OpenStack pour la région spécifiée
        conn = openstack.connect(region_name=region)
        headers = {'X-Auth-Token': conn.session.get_token()}
        
        # Tentative d'obtenir les informations de version depuis l'API
        response = requests.get(f"{cloudkitty_endpoint}/v1", headers=headers)
        
        if response.status_code == 200:
            version_info = response.json()
            print(f"Version de CloudKitty dans la région {region}: {version_info}")
            return version_info
        else:
            print(f"Impossible d'obtenir la version de CloudKitty dans la région {region}. Code d'état: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Erreur lors de l'obtention de la version de CloudKitty dans la région {region}: {e}")
        return None

def setup_cloudkitty(region='dc3-a'):
    """Configure CloudKitty et retourne un client CloudKitty"""
    url_region = region_to_url_id(region)
    if check_cloudkitty_version(region):
        try:
            # Créer une connexion OpenStack pour la région spécifiée
            conn = openstack.connect(region_name=region)
            
            # Obtenir le token d'authentification pour les requêtes à CloudKitty
            auth_token = conn.session.get_token()
            
            # Configuration de l'URL CloudKitty
            cloudkitty_endpoint = f"https://api.{url_region}.infomaniak.cloud/rating"
            
            # Retourner un "client" CloudKitty (en réalité, juste les informations nécessaires pour les requêtes HTTP)
            return {
                'endpoint': cloudkitty_endpoint,
                'token': auth_token,
                'region': region
            }, region
        except Exception as e:
            print(f"Erreur lors de la configuration de CloudKitty pour la région {region}: {e}")
    
    return None, region

def get_all_regions_cloudkitty():
    """Essaie de configurer CloudKitty dans toutes les régions disponibles"""
    # Essayer de configurer CloudKitty dans les différentes régions
    regions = ['dc3-a', 'dc4-a']
    
    for region in regions:
        cloudkitty, region = setup_cloudkitty(region)
        if cloudkitty:
            return cloudkitty, region
    
    return None, None

def get_instance_summary(instance_id, cloudkitty, start_date=None, end_date=None):
    """Récupère le résumé des coûts d'une instance via CloudKitty"""
    if not cloudkitty:
        return None
    
    # Si pas de dates spécifiées, utiliser les 30 derniers jours
    if not start_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
    
    # Formatage des dates pour CloudKitty
    start_str = start_date.strftime('%Y-%m-%dT00:00:00')
    end_str = end_date.strftime('%Y-%m-%dT23:59:59')
    
    try:
        # Construire l'URL pour la requête
        url = f"{cloudkitty['endpoint']}/v1/summary"
        
        # Paramètres de la requête
        params = {
            'begin': start_str,
            'end': end_str,
            'filters': json.dumps({
                'resource_id': instance_id
            })
        }
        
        # En-têtes avec le token d'authentification
        headers = {
            'X-Auth-Token': cloudkitty['token'],
            'Content-Type': 'application/json'
        }
        
        # Effectuer la requête
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Erreur lors de la récupération des données de facturation. Code: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"Exception lors de la récupération des données de facturation: {e}")
        return None

# Formatage de la taille
def format_size(size_bytes):
    """Formater la taille en unités lisibles"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

# Formatage de la date
def format_date(date_string):
    """Formater une date ISO en format lisible"""
    if not date_string:
        return "N/A"
    try:
        date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return date_string

# Lister les images
def list_images(conn):
    print_header("LISTE DES IMAGES")
    # Récupérer les images
    images = list(conn.image.images())

    # Trier les images par date de création
    images.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else '', reverse=True)

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<30} {'ID':<36} {'Taille':<15} {'Date de création':<25}")
    print("-" * 106)
    for image in images:
        size_formatted = format_size(image.size) if hasattr(image, 'size') else "N/A"
        created_date = format_date(image.created_at) if hasattr(image, 'created_at') else "N/A"
        print(f"{image.name:<30} {image.id:<36} {size_formatted:<15} {created_date:<25}")

# Lister les instances
def list_instances(conn, cloudkitty=None):
    print_header("LISTE DES INSTANCES")
    # Récupérer les serveurs
    servers = list(conn.compute.servers())

    # Trier les serveurs par date de création
    servers.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else '', reverse=True)

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<30} {'ID':<36} {'Statut':<15} {'Date de création':<25}")
    print("-" * 106)
    for server in servers:
        created_date = format_date(server.created_at) if hasattr(server, 'created_at') else "N/A"
        print(f"{server.name:<30} {server.id:<36} {server.status:<15} {created_date:<25}")
        
        # Si CloudKitty est configuré, essayer de récupérer les informations de facturation
        if cloudkitty:
            summary = get_instance_summary(server.id, cloudkitty)
            if summary and 'results' in summary:
                total = sum(item.get('qty', 0) * item.get('price', 0) for item in summary['results'])
                print(f"  Coût estimé des 30 derniers jours: {total:.2f} EUR")

# Lister les snapshots
def list_snapshots(conn):
    print_header("LISTE DES SNAPSHOTS")
    # Récupérer les snapshots
    snapshots = list(conn.block_storage.snapshots())

    # Trier les snapshots par date de création
    snapshots.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else '', reverse=True)

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<30} {'ID':<36} {'Taille':<15} {'Date de création':<25}")
    print("-" * 106)
    for snapshot in snapshots:
        size_formatted = f"{snapshot.size} GB" if hasattr(snapshot, 'size') else "N/A"
        created_date = format_date(snapshot.created_at) if hasattr(snapshot, 'created_at') else "N/A"
        print(f"{snapshot.name:<30} {snapshot.id:<36} {size_formatted:<15} {created_date:<25}")

# Lister les backups
def list_backups(conn):
    print_header("LISTE DES BACKUPS")
    # Récupérer les backups
    backups = list(conn.block_storage.backups())

    # Trier les backups par date de création
    backups.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else '', reverse=True)

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<30} {'ID':<36} {'Taille':<15} {'Date de création':<25}")
    print("-" * 106)
    for backup in backups:
        size_formatted = f"{backup.size} GB" if hasattr(backup, 'size') else "N/A"
        created_date = format_date(backup.created_at) if hasattr(backup, 'created_at') else "N/A"
        print(f"{backup.name:<30} {backup.id:<36} {size_formatted:<15} {created_date:<25}")

# Lister les volumes
def list_volumes(conn):
    print_header("LISTE DES VOLUMES")
    # Récupérer les volumes
    volumes = list(conn.block_storage.volumes())

    # Trier les volumes par date de création
    volumes.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else '', reverse=True)

    # Afficher les en-têtes du tableau
    print(f"{'Nom':<30} {'ID':<36} {'Taille':<15} {'Date de création':<25}")
    print("-" * 106)
    for volume in volumes:
        size_formatted = f"{volume.size} GB" if hasattr(volume, 'size') else "N/A"
        created_date = format_date(volume.created_at) if hasattr(volume, 'created_at') else "N/A"
        print(f"{volume.name:<30} {volume.id:<36} {size_formatted:<15} {created_date:<25}")

# Organiser les volumes par instance
def mounted_volumes(conn):
    instances = list(conn.compute.servers())
    volumes = list(conn.block_storage.volumes())
    
    tree = {}
    
    for instance in instances:
        tree[instance.name] = []
        for attachment in instance.attached_volumes:
            for volume in volumes:
                if volume.id == attachment['id']:
                    tree[instance.name].append(volume.name)

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
