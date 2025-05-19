#!/usr/bin/env python3
import json
import requests

def load_usages(filename):
    try:
        with open(filename, "r") as f:
            usages = json.load(f)
            print("\n📊 Récapitulatif des usages par projet :")
            for pid, data in usages.items():
                print(f" - Projet {pid}: CPU={data['cpu']}, RAM={data['ram']}, Storage={data['storage']}, ICU={data.get('icu', 0)}")
            return usages
    except Exception:
        return {}

def load_billing():
    # Placeholder for loading billing data
    return {}

def aggregate_costs(data):
    # Placeholder for aggregating costs
    return {}

def select_project_interactive(usages):
    projects = list(usages.keys())
    for i, pid in enumerate(projects, start=1):
        print(f"  {i}. {pid}")
    while True:
        choice = input(f"Choisissez un projet (1-{len(projects)}): ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(projects):
                return projects[idx - 1]
        print("Choix invalide. Veuillez entrer un numéro valide.")

def main():
    start_iso = "2025-05-18T14:00:00+00:00"
    end_iso = "2025-05-18T15:00:00+00:00"

    # Charger usages APRÈS génération
    usages = load_usages("fetch_uses.json")

    # Exemple d'ajout des logs pour la récupération des mesures depuis Gnocchi
    # Supposons que nous avons une structure usages qui contient des resource_id et metrics
    # Cette partie simule la récupération des mesures et affiche les logs demandés
    for resource_id, metrics in usages.items():
        for metric in ['cpu', 'ram', 'storage', 'icu']:
            if metric in metrics:
                url = f"http://gnocchi.example.com/v1/metric/{resource_id}/{metric}/measures"
                try:
                    measure_resp = requests.get(url)
                    print(f"↪️ Récupération des mesures pour {resource_id} / {metric}: status={measure_resp.status_code}")
                    if measure_resp.status_code == 200:
                        data_points = measure_resp.json()
                        print(f"  - {len(data_points)} points")
                        if data_points:
                            print("    Premier point :", data_points[0])
                except Exception as e:
                    print(f"Erreur lors de la récupération des mesures pour {resource_id} / {metric}: {e}")

    if not usages:
        print("⚠️ Aucun usage détecté dans fetch_uses.json, mais on poursuit avec les coûts uniquement.")
        data = load_billing()
        aggregated = aggregate_costs(data)
        if not aggregated:
            print("⚠️ Aucun coût détecté dans la facturation non plus. Fin du programme.")
            return
        projects = list(aggregated.keys())
        print("\nProjets disponibles (coûts) :")
        for i, pid in enumerate(projects, start=1):
            print(f"  {i}. {pid}")
        while True:
            choice = input(f"Choisissez un projet (1-{len(projects)}): ").strip()
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(projects):
                    project_id = projects[idx - 1]
                    break
            print("Choix invalide. Veuillez entrer un numéro valide.")
    else:
        print("\nProjets disponibles dans fetch_uses.json :")
        for i, pid in enumerate(usages.keys(), start=1):
            print(f"  {i}. {pid}")
        project_id = select_project_interactive(usages)

    print(f"Projet sélectionné : {project_id}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import os
import sys
import json
import requests

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