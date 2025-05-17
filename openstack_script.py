#!/usr/bin/env python3

import subprocess
import sys
import importlib

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

try:
    importlib.import_module('gnocchiclient')
except ImportError:
    print("Installation du package Gnocchi...")
    install_package('python-gnocchiclient')

import openstack
from datetime import datetime

from gnocchiclient.client import Client as GnocchiClient
from gnocchiclient.v1 import metric

# Se connecter à OpenStackv 
from dotenv import load_dotenv
import os

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
if conn.authorize():
    print("Connexion réussie à OpenStack")
else:
    print("Échec de la connexion à OpenStack")
    exit(1)

# Fonction pour afficher les en-têtes
def print_header(header):
    print("\n" + "=" * 50)
    print(header.center(50))
    print("=" * 50 + "\n")

# Fonction pour configurer le client Gnocchi
def get_gnocchi_client():
    gnocchi = GnocchiClient('1', session=conn.session)
    return gnocchi

# Fonction pour récupérer les métriques de coûts des flavors
def get_flavor_costs(gnocchi, flavor_id):
    # Note: Vous devez adapter cette partie en fonction de la structure de vos métriques dans Gnocchi
    try:
        # Exemple: Récupérer la dernière mesure de coût pour la flavor
        measures = gnocchi.measure.get_measures(metric=flavor_id, aggregation='mean')
        if measures:
            return measures[-1][1]  # Supposons que le coût est la dernière mesure
    except Exception as e:
        print(f"Erreur lors de la récupération des coûts pour la flavor {flavor_id}: {e}")
    return 0.0

def calculate_instance_cost(flavor_id, uptime, gnocchi):
    # Récupérer le coût horaire de la flavor
    hourly_cost = get_flavor_costs(gnocchi, flavor_id)
    # Calculer le coût total en fonction de l'uptime
    uptime_hours = uptime.total_seconds() / 3600
    total_cost = uptime_hours * hourly_cost

    return total_cost

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

list_images(conn)

# Lister les instances
def list_instances(conn):
    print_header("LISTE DES INSTANCES")
    # Récupérer les instances
    instances = list(conn.compute.servers())
    # Récupérer toutes les flavors disponibles
    flavors = {flavor.id: flavor for flavor in conn.compute.flavors()}

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Flavor ID':<20} {'Uptime':<20}" {'Coût total':<20})
    print("-" * 116)
    for instance in instances:
        flavor_id = instance.flavor['id']
        # Convertir la date de création en objet datetime
        created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
        # Calculer l'uptime
        uptime = datetime.now() - created_at
        # Formater l'uptime en jours, heures, minutes, secondes
        uptime_str = str(uptime).split('.')[0]  # Supprimer les microsecondes
        # Calculer le coût total
        total_cost = calculate_instance_cost(flavor_id, uptime, gnocchi)
        print(f"{instance.id:<36} {instance.name:<20} {flavor_id:<20} {uptime_str:<20} {total_cost:<20.2f}")

list_instances(conn)

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
    
list_snapshots(conn)

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

list_backups(conn)

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

list_volumes(conn)

# Lister les volumes sous forme d'arborescence
print_header("ARBORESCENCE DES VOLUMES")
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

# Obtenir l'arborescence des volumes montés
tree = mounted_volumes(conn)
print_tree(tree)

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

list_floating_ips(conn)

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

list_containers(conn)