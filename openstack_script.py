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

import openstack

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

def print_header(header):
    print("\n" + "=" * 50)
    print(header.center(50))
    print("=" * 50 + "\n")

# Lister les images privées et partagées
def list_images(conn):
    print_header("LISTE DES IMAGES PRIVÉES ET PARTAGÉES UTILISEES PAR L'UTILISATEUR")
    # Récupérer les images privées et les convertir en liste
    private_images = list(conn.image.images(visibility='private'))

    # Récupérer les images partagées et les convertir en liste
    shared_images = list(conn.image.images(visibility='shared'))

    # Combiner les images privées et partagées
    all_images = private_images + shared_images

    for image in all_images:
        print(f"ID: {image.id}, Nom: {image.name}, Visibilité: {image.visibility}")

list_images(conn)

# Lister les instances
def list_instances(conn):
    print_header("LISTE DES INSTANCES AVEC LES DÉTAILS DES FLAVORS")
    # Récupérer les instances
    instances = list(conn.compute.servers())

    # Récupérer toutes les flavors disponibles
    flavors = {flavor.id: flavor for flavor in conn.compute.flavors()}
    # Récupérer l'âge des instances
    creation_times = {}
    for instance in instances:
        if instance.created_at:
            creation_times[instance.id] = instance.created_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            creation_times[instance.id] = "N/A"

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Flavor ID':<20} {'Uptime':<20}")
    print("-" * 96)

    for instance in instances:
        flavor_id = instance.flavor['id']
        print(f"{instance.id:<36} {instance.name:<20} {flavor_id:<20} {creation_times[instance.id]:<20}")

list_instances(conn)

# Lister les snapshots
print_header("LISTE DES SNAPSHOTS")
for snapshot in conn.block_storage.snapshots():
    print(snapshot)

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

    # Récupérer toutes les IDs des IP flottantes
    floating_ip_ids = [ip.id for ip in floating_ips]
    # Récupérer les IP des IP flottantes
    floating_ip_addresses = [ip.floating_ip_address for ip in floating_ips]
    # Récupérer l'état des IP flottantes
    floating_ip_statuses = [ip.status for ip in floating_ips]

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