#!/usr/bin/env python3

from openstack import connection
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json

# Configuration de la connexion à OpenStack
auth_url = 'http://<your-openstack-auth-url>/v3'
project_name = '<your-project-name>'
username = '<your-username>'
password = '<your-password>'
user_domain_name = '<your-user-domain-name>'
project_domain_name = '<your-project-domain-name>'

# Connexion à OpenStack
conn = connection.Connection(
    auth_url=auth_url,
    project_name=project_name,
    username=username,
    password=password,
    user_domain_name=user_domain_name,
    project_domain_name=project_domain_name
)

def get_inactive_instances():
    # Récupérer la liste des instances
    servers = conn.compute.servers()

    inactive_instances = []
    for server in servers:
        # Vérifier si l'instance est inactive (par exemple, CPU usage faible)
        # Ici, vous pouvez ajouter des critères spécifiques pour déterminer si une instance est inactive
        if server.status == 'ACTIVE':
            # Ajoutez votre logique pour vérifier l'inactivité ici
            # Par exemple, vérifier les métriques de performance via l'API de surveillance
            inactive_instances.append(server)

    return inactive_instances

def get_unused_volumes():
    # Récupérer la liste des volumes
    volumes = conn.block_storage.volumes()

    unused_volumes = []
    for volume in volumes:
        # Vérifier si le volume est non utilisé (par exemple, non attaché à une instance)
        if not volume.attachments:
            unused_volumes.append(volume)

    return unused_volumes

def analyze_resource_usage():
    # Collecter les données d'utilisation des ressources
    # Ici, vous pouvez ajouter votre logique pour collecter les données d'utilisation des ressources
    # Par exemple, utiliser l'API de surveillance pour obtenir les métriques de performance
    data = {
        'Instance': ['Instance1', 'Instance2', 'Instance3'],
        'CPU Usage (%)': [10, 20, 30],
        'RAM Usage (%)': [15, 25, 35],
        'Disk Usage (%)': [20, 30, 40]
    }

    df = pd.DataFrame(data)

    # Analyser les données
    # Par exemple, calculer la moyenne et l'écart type
    mean_cpu = df['CPU Usage (%)'].mean()
    std_cpu = df['CPU Usage (%)'].std()

    mean_ram = df['RAM Usage (%)'].mean()
    std_ram = df['RAM Usage (%)'].std()

    mean_disk = df['Disk Usage (%)'].mean()
    std_disk = df['Disk Usage (%)'].std()

    # Générer des visualisations
    plt.figure(figsize=(12, 6))
    sns.barplot(x='Instance', y='CPU Usage (%)', data=df)
    plt.title('CPU Usage by Instance')
    plt.savefig('cpu_usage.png')

    plt.figure(figsize=(12, 6))
    sns.barplot(x='Instance', y='RAM Usage (%)', data=df)
    plt.title('RAM Usage by Instance')
    plt.savefig('ram_usage.png')

    plt.figure(figsize=(12, 6))
    sns.barplot(x='Instance', y='Disk Usage (%)', data=df)
    plt.title('Disk Usage by Instance')
    plt.savefig('disk_usage.png')

    # Générer un rapport
    report = f"Rapport d'analyse de l'utilisation des ressources:\n\n"
    report += f"Moyenne de l'utilisation du CPU: {mean_cpu:.2f}%\n"
    report += f"Écart type de l'utilisation du CPU: {std_cpu:.2f}%\n\n"
    report += f"Moyenne de l'utilisation de la RAM: {mean_ram:.2f}%\n"
    report += f"Écart type de l'utilisation de la RAM: {std_ram:.2f}%\n\n"
    report += f"Moyenne de l'utilisation du disque: {mean_disk:.2f}%\n"
    report += f"Écart type de l'utilisation du disque: {std_disk:.2f}%\n\n"

    return report

def calculate_underutilized_costs():
    try:
        with open('weekly_billing.json', 'r') as f:
            billing_data = json.load(f)
    except FileNotFoundError:
        print("Le fichier weekly_billing.json est introuvable.")
        billing_data = {}
    except json.JSONDecodeError:
        print("Erreur lors de la lecture du fichier weekly_billing.json : format JSON invalide.")
        billing_data = {}

    # Exemple de coûts en ICU (unité interne)
    underutilized_costs_icu = {
        'Inactive Instances': 5000,  # Exemple de coût en ICU
        'Unused Volumes': 3000       # Exemple de coût en ICU
    }

    # Taux de conversion
    ICU_to_CHF = 1 / 50       # 1 CHF = 50 ICU → 1 ICU = 0.02 CHF
    ICU_to_EUR = 1 / 55.5     # 1 EUR = 55.5 ICU → 1 ICU ≈ 0.01802 EUR

    underutilized_costs = {}
    for resource, cost_icu in underutilized_costs_icu.items():
        cost_chf = cost_icu * ICU_to_CHF
        cost_eur = cost_icu * ICU_to_EUR
        underutilized_costs[resource] = {
            'ICU': cost_icu,
            'CHF': round(cost_chf, 2),
            'EUR': round(cost_eur, 2)
        }

    return underutilized_costs

def collect_and_analyze_data():
    inactive_instances = get_inactive_instances()
    unused_volumes = get_unused_volumes()

    report_body = "Récapitulatif des ressources sous-utilisées:\n\n"
    report_body += "Instances inactives:\n"
    for instance in inactive_instances:
        report_body += f"ID: {instance.id}, Nom: {instance.name}\n"

    report_body += "\nVolumes non utilisés:\n"
    for volume in unused_volumes:
        report_body += f"ID: {volume.id}, Nom: {volume.name}\n"

    report = analyze_resource_usage()
    report_body += "\n" + report

    underutilized_costs = calculate_underutilized_costs()
    report_body += "\nCoûts des ressources sous-utilisées:\n"
    for resource, costs in underutilized_costs.items():
        report_body += f"{resource}: {costs['ICU']} ICU / {costs['CHF']} CHF / {costs['EUR']} EUR\n"

    return report_body

if __name__ == '__main__':
    report_body = collect_and_analyze_data()
    with open('/tmp/openstack_report.txt', 'w') as f:
        f.write(report_body)
