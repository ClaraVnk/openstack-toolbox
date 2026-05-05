#!/usr/bin/env python3

import json
import subprocess
from datetime import datetime, timedelta, timezone

from openstack import connection
from rich import print
from rich.console import Console
from rich.table import Table

from .config import get_language_preference, load_openstack_credentials
from .utils import get_version, isoformat

# Dictionnaire des traductions
TRANSLATIONS = {
    "fr": {
        "welcome": "🎉 Bienvenue dans OpenStack Toolbox 🧰 v{} 🎉",
        "missing_vars": "❌ Variables OpenStack manquantes : {}",
        "connection_error": "❌ Impossible de charger les identifiants OpenStack. Vérifiez votre configuration.",
        "auth_error": "❌ Échec de la connexion à OpenStack",
        "billing_period": "📅 Période choisie automatiquement : la semaine dernière {} → {}",
        "billing_error": "❌ Échec de la récupération des données : {}",
        "billing_exception": "❌ Exception lors de la récupération du billing : {}",
        "flavor_parse_error": "❌ Échec du parsing pour le flavor '{}' : {}",
        "openstack_error": "❌ La commande `openstack server list` a échoué.",
        "cli_error": "❌ Erreur lors de l'appel à `openstack server list`: {}",
        "no_inactive": "✅ Aucune instance inactive détectée.",
        "no_unused": "✅ Aucun volume inutilisé détecté.",
        "no_billing": "❌ Aucune donnée de facturation disponible (trop faibles ou non disponibles).",
        "billing_json_error": "❌ Erreur lors de la lecture des données de facturation : format JSON invalide.",
        "report_title": "RÉCAPITULATIF HEBDOMADAIRE DES RESSOURCES SOUS-UTILISÉES",
        "inactive_instances": "INSTANCES INACTIVES",
        "unused_volumes": "VOLUMES NON UTILISÉS",
        "underutilized_costs": "COÛTS DES RESSOURCES SOUS-UTILISÉES",
        "report_generated": "🎉 Rapport généré avec succès : {}",
        "resource": "Ressource",
        "status": "Statut",
        "name": "Nom",
    },
    "en": {
        "welcome": "🎉 Welcome to OpenStack Toolbox 🧰 v{} 🎉",
        "missing_vars": "❌ Missing OpenStack variables: {}",
        "connection_error": "❌ Unable to load OpenStack credentials. Please check your configuration.",
        "auth_error": "❌ Failed to connect to OpenStack",
        "billing_period": "📅 Automatically selected period: last week {} → {}",
        "billing_error": "❌ Failed to retrieve data: {}",
        "billing_exception": "❌ Exception while retrieving billing: {}",
        "flavor_parse_error": "❌ Failed to parse flavor '{}': {}",
        "openstack_error": "❌ The `openstack server list` command failed.",
        "cli_error": "❌ Error calling `openstack server list`: {}",
        "no_inactive": "✅ No inactive instances detected.",
        "no_unused": "✅ No unused volumes detected.",
        "no_billing": "❌ No billing data available (too low or unavailable).",
        "billing_json_error": "❌ Error reading billing data: invalid JSON format.",
        "report_title": "WEEKLY SUMMARY OF UNDERUTILIZED RESOURCES",
        "inactive_instances": "INACTIVE INSTANCES",
        "unused_volumes": "UNUSED VOLUMES",
        "underutilized_costs": "COSTS OF UNDERUTILIZED RESOURCES",
        "report_generated": "🎉 Report generated successfully: {}",
        "resource": "Resource",
        "status": "Status",
        "name": "Name",
    },
}


# Fonction pour générer le fichier de billing
def generate_billing():
    lang = get_language_preference()
    try:
        today = datetime.now(timezone.utc).date()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        start_dt = datetime.combine(last_monday, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(last_sunday, datetime.max.time()).replace(tzinfo=timezone.utc)

        print(TRANSLATIONS[lang]["billing_period"].format(start_dt, end_dt))

        start_iso = isoformat(start_dt)
        end_iso = isoformat(end_dt)

        cmd = [
            "openstack",
            "rating",
            "dataframes",
            "get",
            "-b",
            start_iso,
            "-e",
            end_iso,
            "-c",
            "Resources",
            "-f",
            "json",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            return result.stdout
        else:
            return TRANSLATIONS[lang]["billing_error"].format(result.stderr.strip())
    except Exception as e:
        return TRANSLATIONS[lang]["billing_exception"].format(e)


console = Console()


# Fonction pour récupérer les statuts des VMs via l'API OpenStack
def get_vm_statuses_from_cli():
    lang = get_language_preference()
    try:
        result = subprocess.run(
            ["openstack", "server", "list", "-f", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(TRANSLATIONS[lang]["openstack_error"])
            print("STDERR:", result.stderr)
            return []
        servers = json.loads(result.stdout)
        return [
            {
                "id": s["ID"],
                "name": s["Name"],
                "status": s["Status"],
                "project": s.get("Project ID", "inconnu"),
            }
            for s in servers
        ]
    except Exception as e:
        print(TRANSLATIONS[lang]["cli_error"].format(e))
        return []


# Liste des statuts de VM à vérifier
def get_inactive_instances_from_cli():
    servers = get_vm_statuses_from_cli()
    inactive = [s for s in servers if s["status"].upper() != "ACTIVE"]
    return inactive


def get_unused_volumes(conn):
    # Récupérer la liste des volumes
    volumes = conn.block_storage.volumes()

    unused_volumes = []
    for volume in volumes:
        # Vérifier si le volume est non utilisé (par exemple, non attaché à une instance)
        if not volume.attachments:
            unused_volumes.append(volume)

    return unused_volumes


def calculate_underutilized_costs(billing_json):
    lang = get_language_preference()
    ICU_to_CHF = 1 / 50
    ICU_to_EUR = 1 / 55.5

    try:
        billing_data = json.loads(billing_json)
    except json.JSONDecodeError:
        print(TRANSLATIONS[lang]["billing_json_error"])
        return {}

    underutilized_costs = {}
    for entry in billing_data:
        resource = entry.get("name") or entry.get("resource") or entry.get("ID") or entry.get("id")
        cost_icu = (
            entry.get("rate:unit") or entry.get("ICU") or entry.get("icu") or entry.get("cost") or entry.get("rate:sum")
        )
        if resource is not None and cost_icu is not None:
            try:
                cost_icu = float(cost_icu)
            except Exception:
                continue
            cost_chf = cost_icu * ICU_to_CHF
            cost_eur = cost_icu * ICU_to_EUR
            underutilized_costs[resource] = {
                "ICU": cost_icu,
                "CHF": round(cost_chf, 2),
                "EUR": round(cost_eur, 2),
            }
    return underutilized_costs


def collect_and_analyze_data(conn, billing_json=None):
    lang = get_language_preference()
    inactive_instances = get_inactive_instances_from_cli()
    unused_volumes = get_unused_volumes(conn)

    report_body = ""
    report_body += "=" * 60 + "\n"
    report_body += TRANSLATIONS[lang]["report_title"] + "\n"
    report_body += "=" * 60 + "\n\n"

    report_body += f"[{TRANSLATIONS[lang]['inactive_instances']}]\n"
    if inactive_instances:
        table = Table(title="")
        table.add_column("ID", style="magenta")
        table.add_column(TRANSLATIONS[lang]["name"], style="cyan")
        table.add_column(TRANSLATIONS[lang]["status"], style="red")
        for instance in inactive_instances:
            table.add_row(instance["id"], instance["name"], instance["status"])
        console.print(table)
    else:
        report_body += TRANSLATIONS[lang]["no_inactive"] + "\n"
    report_body += "\n" + "-" * 50 + "\n"

    report_body += f"[{TRANSLATIONS[lang]['unused_volumes']}]\n"
    if unused_volumes:
        table = Table(title="")
        table.add_column("ID", style="magenta")
        table.add_column(TRANSLATIONS[lang]["name"], style="cyan")
        for volume in unused_volumes:
            table.add_row(volume.id, volume.name)
        console.print(table)
    else:
        report_body += TRANSLATIONS[lang]["no_unused"] + "\n"
    report_body += "\n" + "-" * 50 + "\n"

    report_body += f"[{TRANSLATIONS[lang]['underutilized_costs']}]\n"
    underutilized_costs = calculate_underutilized_costs(billing_json) if billing_json else {}
    if not underutilized_costs:
        report_body += TRANSLATIONS[lang]["no_billing"] + "\n"
    else:
        table = Table(title="")
        table.add_column(TRANSLATIONS[lang]["resource"], style="cyan")
        table.add_column("CHF", justify="right", style="green")
        table.add_column("EUR", justify="right", style="blue")
        for resource, costs in underutilized_costs.items():
            table.add_row(resource, f"{costs['CHF']} CHF", f"{costs['EUR']} EUR")
        console.print(table)
    report_body += "\n" + "-" * 50 + "\n"

    return report_body


def main():
    lang = get_language_preference()
    version = get_version()
    print(f"[yellow bold]{TRANSLATIONS[lang]['welcome'].format(version)}[/yellow bold]")
    header = r"""
  ___                       _             _
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\
 / _ \|_|__ | |_(_)_ __ ___ (_)______ _| |_(_) ___  _ __
| | | | '_ \| __| | '_ ` _ \| |_  / _` | __| |/ _ \| '_ \
| |_| | |_) | |_| | | | | | | |/ / (_| | |_| | (_) | | | |
 \___/| .__/ \__|_|_| |_| |_|_/___\__,_|\__|_|\___/|_| |_|
      |_|
         By Loutre

"""
    print(header)

    # Test des credentials
    creds, missing_vars = load_openstack_credentials()
    if not creds:
        print(f"[bold red]{TRANSLATIONS[lang]['connection_error']}[/bold red]")
        return

    conn = connection.Connection(**creds)
    try:
        if not conn.authorize():
            print(f"[bold red]{TRANSLATIONS[lang]['auth_error']}[/bold red]")
            return

        billing_json = generate_billing()
        report_body = collect_and_analyze_data(conn, billing_json)

        try:
            with open("openstack_optimization_report.txt", "w") as f:
                f.write(report_body)
            print(
                f"[bold green]{TRANSLATIONS[lang]['report_generated'].format('openstack_optimization_report.txt')}[/bold green]"
            )
        except OSError as e:
            print(f"[bold red]❌ Impossible d'écrire le rapport : {e}[/bold red]")

        print(report_body)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
