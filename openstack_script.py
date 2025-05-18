#!/usr/bin/env python3

import subprocess
import sys
import importlib
import json
from datetime import datetime, timedelta, timezone
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

def get_billing_data_from_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def calculate_instance_cost(billing_data, instance_id=None, icu_to_chf=50, icu_to_euro=55.5):
    if not billing_data:
        print(f"Aucune donnée de facturation disponible pour l'instance {instance_id}")
        return 0.0, 0.0

    total_icu = 0.0

    for group in billing_data:
        resources = group.get("Resources", [])
        for resource in resources:
            desc = resource.get("desc", {})
            resource_id = desc.get("id")
            if instance_id and resource_id != instance_id:
                continue  # ignorer les autres

            try:
                price = float(resource.get("rating", 0))
                total_icu += price
            except (TypeError, ValueError):
                continue

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
def list_instances(conn, billing_data):
    print_header("LISTE DES INSTANCES")
    # Récupérer les instances
    instances = list(conn.compute.servers())  # Assurez-vous que cette ligne est exécutée
    # Taux de conversion ICU vers monnaies
    icu_to_chf = 50  # Taux de conversion ICU vers CHF
    icu_to_euro = 55.5  # Taux de conversion ICU vers EUR

    # Afficher les en-têtes du tableau
    print(f"{'ID':<36} {'Nom':<20} {'Flavor ID':<20} {'Uptime':<20} {'Coût (CHF)':<12} {'Coût (EUR)':<12}")
    print("-" * 130)

    # Définir la période pour les données de facturation (30 derniers jours)
    start_time = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:00:00+00:00")
    end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00+00:00")
    print(f"Période de facturation: {start_time} à {end_time}")  # Ajout pour le débogage

    for instance in instances:
        flavor_id = instance.flavor['id']
        # Convertir la date de création en objet datetime
        created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
        # Calculer l'uptime
        uptime = datetime.now() - created_at
        # Formater l'uptime en jours, heures, minutes, secondes
        uptime_str = str(uptime).split('.')[0]  # Supprimer les microsecondes

        # Calculer le coût en CHF et EUR
        cost_chf, cost_euro = calculate_instance_cost(billing_data, instance_id=instance.id)
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
    
    start_time = input("Entrer la date de début (format YYYY-MM-DDTHH:MM:SS+00:00) : ")
    end_time = input("Entrer la date de fin (format YYYY-MM-DDTHH:MM:SS+00:00) : ")
    billing_data = get_billing_data_from_file('billing.json')
    
    # Lister les ressources
    list_images(conn)
    list_instances(conn, billing_data)
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