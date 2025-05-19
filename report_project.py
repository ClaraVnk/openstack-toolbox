#!/usr/bin/env python3

import subprocess
import sys
import importlib
import json
import os

def print_header(header):
    print("\n" + "=" * 50)
    print(header.center(50))
    print("=" * 50 + "\n")

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def load_openstack_credentials():
    load_dotenv()  # essaie de charger depuis .env s’il existe

    creds = {
        "auth_url": os.getenv("OS_AUTH_URL"),
        "project_name": os.getenv("OS_PROJECT_NAME"),
        "username": os.getenv("OS_USERNAME"),
        "password": os.getenv("OS_PASSWORD"),
        "user_domain_name": os.getenv("OS_USER_DOMAIN_NAME"),
        "project_domain_name": os.getenv("OS_PROJECT_DOMAIN_NAME"),
    }

    # Si une des variables est absente, on essaie de charger depuis un fichier JSON
    if not all(creds.values()):
        try:
            with open("secrets.json") as f:
                creds = json.load(f)
        except FileNotFoundError:
            raise RuntimeError("Aucun identifiant OpenStack disponible (.env ou secrets.json manquant)")

    return creds

# Fonction pour obtenir les détails d'un projet spécifique
def get_project_details(conn, project_id):
    print_header(f"DÉTAILS DU PROJET AVEC ID: {project_id}")
    project = conn.identity.get_project(project_id)

    if project:
        print(f"ID: {project.id}")
        print(f"Nom: {project.name}")
        print(f"Description: {project.description}")
        print(f"Domaine: {project.domain_id}")
        print(f"Actif: {'Oui' if project.is_enabled else 'Non'}")
    else:
        print(f"Aucun projet trouvé avec l'ID: {project_id}")

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

from dotenv import load_dotenv
from openstack import connection

# Connexion à OpenStack
creds = load_openstack_credentials()
conn = connection.Connection(**creds)

# Conversion des tarifs
TARIFS_ICU = {
    "vcpu_hour": 2.0,
    "ram_gb_hour": 0.5,
    "storage_gb_hour": 0.2,
    "network_gb": 0.4
}

# Conversion ICU → EUR et CHF
ICU_CONVERSION = {
    "icu_to_eur": 1 / 55.5,  # 1 ICU = 0.018018 EUR
    "icu_to_chf": 1 / 50.0   # 1 ICU = 0.02 CHF
}

# Fonctions métriques
METRICS_KEYS = {
    "vcpu_hour": "cpu_hours",
    "ram_gb_hour": "ram_gb_hours",
    "storage_gb_hour": "storage_gb_hours",
    "network_gb": "network_gb"
}

def load_billing_data(filepath="weekly_billing.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def calculate_costs(entry):
    cpu = float(entry.get(METRICS_KEYS["vcpu_hour"], 0))
    ram = float(entry.get(METRICS_KEYS["ram_gb_hour"], 0))
    storage = float(entry.get(METRICS_KEYS["storage_gb_hour"], 0))
    network = float(entry.get(METRICS_KEYS["network_gb"], 0))

    total_icu = (
        cpu * TARIFS_ICU["vcpu_hour"] +
        ram * TARIFS_ICU["ram_gb_hour"] +
        storage * TARIFS_ICU["storage_gb_hour"] +
        network * TARIFS_ICU["network_gb"]
    )
    total_eur = total_icu * ICU_CONVERSION["icu_to_eur"]
    total_chf = total_icu * ICU_CONVERSION["icu_to_chf"]

    return {
        "cpu_h": cpu,
        "ram_h": ram,
        "storage_h": storage,
        "network_gb": network,
        "total_icu": total_icu,
        "total_eur": total_eur,
        "total_chf": total_chf
    }

# Récupération des projets
project_id = input("Entrez l'ID du projet à analyser : ").strip()

# Affichage du rapport
def main():
    if not conn.authorize():
        print("Échec de la connexion à OpenStack")
        return

    print("Connexion réussie à OpenStack")

    header = r"""
  ___                       _             _                       
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __                   
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /                   
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <                    
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\               _   
|  _ \|_|__ ___ (_) ___  ___| |_  |  _ \ ___ _ __   ___  _ __| |_ 
| |_) | '__/ _ \| |/ _ \/ __| __| | |_) / _ \ '_ \ / _ \| '__| __|
|  __/| | | (_) | |  __/ (__| |_  |  _ <  __/ |_) | (_) | |  | |_ 
|_|   |_|  \___// |\___|\___|\__| |_| \_\___| .__/ \___/|_|   \__|
              |__/                          |_|                   
      |_|                                                 
         Openstack SysAdmin Toolbox

"""
    print(header)

    subprocess.run([sys.executable, 'weekly_billing.py'], check=True)
    data = load_billing_data()
    report = []

    for entry in data:
        if entry.get("project_id") != project_id:
            continue
        costs = calculate_costs(entry)
        report.append({
            "projet": entry.get("project_name", project_id),
            **costs
        })

    with open('/tmp/openstack_report.txt', 'w') as f:
        if not report:
            f.write("⚠️  Aucun coût détecté pour ce projet (peut-être trop faible ou inexistant).\n")
        else:
            f.write(f"{'Projet':20} | {'CPU h':>8} | {'RAM h':>8} | {'Stock h':>8} | {'Net GB':>8} | {'ICU':>8} | {'EUR':>8} | {'CHF':>8}\n")
            f.write("-" * 90 + "\n")
            for line in report:
                f.write(
                    f"{line['projet'][:20]:20} | "
                    f"{line['cpu_h']:8.2f} | {line['ram_h']:8.2f} | "
                    f"{line['storage_h']:8.2f} | {line['network_gb']:8.2f} | "
                    f"{line['total_icu']:8.2f} | {line['total_eur']:8.2f} | {line['total_chf']:8.2f}\n"
                )

    print("Rapport généré avec succès : /tmp/openstack_project_report.txt")

    if not report:
        print("⚠️  Aucun coût détecté pour ce projet (peut-être trop faible ou inexistant).")
    else:
        print(f"{'Projet':20} | {'CPU h':>8} | {'RAM h':>8} | {'Stock h':>8} | {'Net GB':>8} | {'ICU':>8} | {'EUR':>8} | {'CHF':>8}")
        print("-" * 90)
        for line in report:
            print(
                f"{line['projet'][:20]:20} | "
                f"{line['cpu_h']:8.2f} | {line['ram_h']:8.2f} | "
                f"{line['storage_h']:8.2f} | {line['network_gb']:8.2f} | "
                f"{line['total_icu']:8.2f} | {line['total_eur']:8.2f} | {line['total_chf']:8.2f}"
            )

if __name__ == '__main__':
    main()