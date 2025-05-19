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