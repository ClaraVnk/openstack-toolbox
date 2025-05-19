#!/usr/bin/env python3
import json

def load_usages(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
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