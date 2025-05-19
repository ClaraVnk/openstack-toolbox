#!/usr/bin/env python3
import os
import sys
import json
import requests
import importlib
import subprocess

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    importlib.import_module('dotenv')
except ImportError:
    print("Installation du package dotenv...")
    install_package('python-dotenv')

from dotenv import load_dotenv

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

def get_auth_token():
    token = os.getenv("OS_TOKEN")
    if not token:
        print("⚠️ OS_TOKEN non défini dans l’environnement.")
        sys.exit(1)
    return token

def get_gnocchi_endpoint():
    endpoint = os.getenv("GNOCCHI_ENDPOINT")
    if not endpoint:
        print("⚠️ GNOCCHI_ENDPOINT non défini dans l’environnement.")
        sys.exit(1)
    return endpoint.rstrip('/')

def fetch_resources(token, endpoint):
    headers = {"X-Auth-Token": token}
    url = f"{endpoint}/v1/resource/instance"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Erreur {resp.status_code} à la récupération des ressources Gnocchi : {resp.text}")
        sys.exit(1)
    return resp.json()

def fetch_measures(token, endpoint, resource_id, metric, start, end):
    headers = {"X-Auth-Token": token}
    params = {"start": start, "end": end}
    url = f"{endpoint}/v1/resource/instance/{resource_id}/metric/{metric}/measures"
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"Erreur {resp.status_code} à la récupération des mesures {metric} pour {resource_id}: {resp.text}")
        return []
    return resp.json()

def aggregate_usage(start_iso, end_iso):
    token = get_auth_token()
    endpoint = get_gnocchi_endpoint()

    resources = fetch_resources(token, endpoint)
    if not resources:
        print("Aucune ressource instance trouvée dans Gnocchi.")
        return {}

    usages = {}
    interval_hours = 5 / 60  # Intervalle d'échantillonnage (5 minutes) en heures

    for res in resources:
        resource_id = res["id"]
        # Essayer d'obtenir project_id fiable
        project_id = res.get("original_resource_id") or res.get("project_id") or "inconnu"

        if project_id not in usages:
            usages[project_id] = {"cpu": 0.0, "ram": 0.0, "storage": 0.0, "icu": 0.0}

        metrics_map = {
            "cpu": "cpu",
            "ram": "memory.usage",
            "storage": "disk.root.size"
        }

        for key, metric in metrics_map.items():
            measures = fetch_measures(token, endpoint, resource_id, metric, start_iso, end_iso)
            if not measures:
                continue
            total = 0.0
            for measure in measures:
                value = float(measure[1])
                total += value * interval_hours
            usages[project_id][key] += total

    return usages

def main():
    if len(sys.argv) != 5:
        print("Usage: fetch_uses.py --start YYYY-MM-DDTHH:MM:SS+00:00 --end YYYY-MM-DDTHH:MM:SS+00:00")
        sys.exit(1)

    start_iso = None
    end_iso = None
    for i in range(1, len(sys.argv), 2):
        if sys.argv[i] == "--start":
            start_iso = sys.argv[i+1]
        elif sys.argv[i] == "--end":
            end_iso = sys.argv[i+1]

    if not start_iso or not end_iso:
        print("Les arguments --start et --end sont obligatoires.")
        sys.exit(1)

    usages = aggregate_usage(start_iso, end_iso)

    usages_list = []
    for pid, data in usages.items():
        entry = {"project_id": pid}
        entry.update(data)
        usages_list.append(entry)

    with open("fetch_uses.json", "w") as f:
        json.dump(usages_list, f, indent=2)

    print(f"✅ Fichier fetch_uses.json généré avec {len(usages_list)} projets.")

if __name__ == "__main__":
    main()