#!/usr/bin/env python3

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import tomli
from openstack import connection
from rich import print
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from src.config import get_language_preference, load_openstack_credentials
from src.utils import format_size, isoformat, print_header

# Dictionnaire des traductions
TRANSLATIONS = {
    "fr": {
        "welcome": "🎉 Bienvenue dans OpenStack Toolbox 🧰 v{} 🎉",
        "missing_vars": "❌ Variables OpenStack manquantes : {}",
        "no_project": "❌ Aucun projet trouvé avec l'ID: {}",
        "no_billing": "❌ Aucune donnée de facturation disponible (indisponible ou trop faible) — les coûts affichés seront à 0.\n",
        "no_instances": "🚫 Aucune instance trouvée.",
        "no_snapshots": "🚫 Aucun snapshot trouvé.",
        "no_backups": "🚫 Aucun backup trouvé.",
        "no_volumes": "🚫 Aucun volume trouvé.",
        "no_floating_ips": "🚫 Aucune IP flottante trouvée.",
        "no_containers": "🚫 Aucun container trouvé.",
        "no_images": "🚫 Aucune image privée ou partagée trouvée.",
        "total_resources": "📊 Total des ressources consommées : {} CPU, {} Go de RAM, {} Go de stockage",
        "total_cost": "💰 Coût total des ressources consommées : {:.2f} CHF, {:.2f} EUR",
        "hourly_cost": "💸 Coût horaire moyen : {:.5f} CHF, {:.5f} EUR",
        "insufficient_data": "💸 Coût horaire moyen : Données insuffisantes",
        "mounted_volumes": "📦 Volumes montés par instance",
        "no_volume_mounted": "🚫 Aucun volume",
        "billing_period": "🗓️ Période de facturation sélectionnée : {} → {}\n",
        "enter_billing_period": "Entrez la période de facturation souhaitée (format: YYYY-MM-DD HH:MM), appuyez sur Entrée pour la valeur par défaut.",
        "start_date": "Date de début",
        "end_date": "Date de fin",
        "billing_error": "❌ Échec de la récupération des données : {}",
        "billing_exception": "❌ Exception lors de la récupération du billing : {}",
        "instances_header": "LISTE DES INSTANCES",
        "name_column": "Nom",
        "images_header": "LISTE DES IMAGES UTILISEES",
        "snapshots_header": "LISTE DES SNAPSHOTS",
        "backups_header": "LISTE DES BACKUPS",
        "volumes_header": "LISTE DES VOLUMES",
        "volumes_tree_header": "ARBORESCENCE DES VOLUMES",
        "floating_ips_header": "LISTE DES FLOATING IPs",
        "containers_header": "LISTE DES CONTAINERS",
    },
    "en": {
        "welcome": "🎉 Welcome to OpenStack Toolbox 🧰 v{} 🎉",
        "missing_vars": "❌ Missing OpenStack variables: {}",
        "no_project": "❌ No project found with ID: {}",
        "no_billing": "❌ No billing data available (unavailable or too low) — costs will be displayed as 0.\n",
        "no_instances": "🚫 No instances found.",
        "no_snapshots": "🚫 No snapshots found.",
        "no_backups": "🚫 No backups found.",
        "no_volumes": "🚫 No volumes found.",
        "no_floating_ips": "🚫 No floating IPs found.",
        "no_containers": "🚫 No containers found.",
        "no_images": "🚫 No private or shared images found.",
        "total_resources": "📊 Total resources consumed: {} vCPUs, {} GB RAM, {} GB storage",
        "total_cost": "💰 Total cost of resources: {:.2f} CHF, {:.2f} EUR",
        "hourly_cost": "💸 Average hourly cost: {:.5f} CHF, {:.5f} EUR",
        "insufficient_data": "💸 Average hourly cost: Insufficient data",
        "mounted_volumes": "📦 Volumes mounted by instance",
        "no_volume_mounted": "🚫 No volume",
        "billing_period": "🗓️ Selected billing period: {} → {}\n",
        "enter_billing_period": "Enter the desired billing period (format: YYYY-MM-DD HH:MM), press Enter for default value.",
        "start_date": "Start date",
        "end_date": "End date",
        "billing_error": "❌ Failed to retrieve data: {}",
        "billing_exception": "❌ Exception while retrieving billing: {}",
        "instances_header": "LIST OF INSTANCES",
        "name_column": "Name",
        "images_header": "LIST OF USED IMAGES",
        "snapshots_header": "LIST OF SNAPSHOTS",
        "backups_header": "LIST OF BACKUPS",
        "volumes_header": "LIST OF VOLUMES",
        "volumes_tree_header": "VOLUMES TREE VIEW",
        "floating_ips_header": "LIST OF FLOATING IPs",
        "containers_header": "LIST OF CONTAINERS",
    },
}


# Fonction pour récupérer la version
def get_version():
    pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    pyproject_path = os.path.abspath(pyproject_path)

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
        version = pyproject_data.get("project", {}).get("version", "unknown")
    except Exception:
        version = "unknown"
    return version


# Ajout des fonctions auxiliaires
def trim_to_minute(dt_str):
    return dt_str.replace("T", " ")[:16]


def input_with_default(prompt, default):
    s = input(f"{prompt} [Défaut: {default}]: ")
    return s.strip() or default


def generate_billing():
    try:
        lang = get_language_preference()
        # Dates par défaut : 2 dernières heures UTC
        default_start_dt = datetime.now(timezone.utc) - timedelta(hours=2)
        default_end_dt = datetime.now(timezone.utc)

        print(TRANSLATIONS[lang]["enter_billing_period"])

        start_input = input_with_default(
            TRANSLATIONS[lang]["start_date"],
            trim_to_minute(isoformat(default_start_dt)),
        )
        end_input = input_with_default(
            TRANSLATIONS[lang]["end_date"], trim_to_minute(isoformat(default_end_dt))
        )

        # Parsing des dates saisies
        try:
            start_dt = datetime.strptime(start_input, "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc
            )
            end_dt = datetime.strptime(end_input, "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc
            )
        except ValueError as e:
            return TRANSLATIONS[lang]["billing_error"].format(
                f"Format de date invalide: {e}"
            )

        start_iso = isoformat(start_dt)
        end_iso = isoformat(end_dt)

        print(TRANSLATIONS[lang]["billing_period"].format(start_iso, end_iso))

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

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return TRANSLATIONS[lang]["billing_error"].format(result.stderr.strip())

    except Exception as e:
        return TRANSLATIONS[lang]["billing_exception"].format(e)


console = Console()


# Fonction pour calculer le coût d'une instance
def calculate_instance_cost(
    billing_data, instance_id=None, icu_to_chf=50, icu_to_euro=55.5
):
    if not billing_data:
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


# Lister les images privées et partagées
def list_images(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["images_header"])
    private_images = list(conn.image.images(visibility="private"))
    shared_images = list(conn.image.images(visibility="shared"))
    all_images = private_images + shared_images

    if not all_images:
        print(TRANSLATIONS[lang]["no_images"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Visibilité", style="green")
    for image in all_images:
        table.add_row(image.id, image.name, image.visibility)
    console.print(table)


def get_instance_details(conn, instance, flavors):
    """
    Récupère les détails d'une instance de manière parallèle.
    """
    lang = get_language_preference()
    try:
        flavor_id = instance.flavor["id"]
        flavor = flavors.get(flavor_id, {"name": TRANSLATIONS[lang]["unknown"]})
        flavor_name = flavor.get("name", TRANSLATIONS[lang]["unknown"])

        created_at = datetime.strptime(instance.created_at, "%Y-%m-%dT%H:%M:%SZ")
        uptime = datetime.now() - created_at
        uptime_str = str(uptime).split(".")[0]

        status = instance.status
        status_color = "green" if status == "ACTIVE" else "red"

        return {
            "id": instance.id,
            "name": instance.name,
            "flavor": flavor_name,
            "status": status,
            "status_color": status_color,
            "uptime": uptime_str,
        }
    except Exception as e:
        print(
            f"[bold red]Erreur lors de la récupération des détails de l'instance {instance.id}: {str(e)}[/bold red]"
        )
        return None


def list_instances(conn):
    """
    Liste toutes les instances avec parallélisation de la collecte des détails.
    """
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["instances_header"])

    instances = list(conn.compute.servers())
    if not instances:
        print(TRANSLATIONS[lang]["no_instances"])
        return

    # Récupération des flavors en une seule fois
    flavors = {f.id: f for f in conn.compute.flavors()}

    # Collecte parallèle des détails des instances
    instance_details = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(get_instance_details, conn, instance, flavors)
            for instance in instances
        ]

        for future in as_completed(futures):
            try:
                details = future.result()
                if details:
                    instance_details.append(details)
            except Exception as e:
                print(
                    f"[bold red]Erreur lors de la récupération des détails d'une instance : {str(e)}[/bold red]"
                )

    # Affichage des résultats
    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column(TRANSLATIONS[lang]["name_column"], style="cyan")
    table.add_column("Flavor", style="green")
    table.add_column("Status", justify="center")
    table.add_column("Uptime", justify="right")

    for details in sorted(instance_details, key=lambda x: x["name"]):
        table.add_row(
            details["id"],
            details["name"],
            details["flavor"],
            f"[{details['status_color']}]{details['status']}[/{details['status_color']}]",
            details["uptime"],
        )

    console = Console()
    console.print(table)


# Lister les snapshots
def list_snapshots(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["snapshots_header"])
    snapshots = list(conn.block_storage.snapshots())

    if not snapshots:
        print(TRANSLATIONS[lang]["no_snapshots"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Volume associé", style="green")
    for snapshot in snapshots:
        table.add_row(snapshot.id, snapshot.name, snapshot.volume_id)
    console.print(table)


# Lister les backups
def list_backups(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["backups_header"])
    backups = list(conn.block_storage.backups())

    if not backups:
        print(TRANSLATIONS[lang]["no_backups"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Volume associé", style="green")
    for backup in backups:
        table.add_row(backup.id, backup.name, backup.volume_id)
    console.print(table)


# Lister les volumes
def list_volumes(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["volumes_header"])
    volumes = list(conn.block_storage.volumes())

    if not volumes:
        print(TRANSLATIONS[lang]["no_volumes"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Attaché", justify="center")
    table.add_column("Snapshot", style="blue")
    for volume in volumes:
        attached = "Oui" if volume.attachments else "Non"
        snapshot_id = volume.snapshot_id[:6] if volume.snapshot_id else "Aucun"
        table.add_row(
            volume.id,
            volume.name,
            str(volume.size),
            volume.volume_type,
            attached,
            snapshot_id,
        )
    console.print(table)


# Récupérer les volumes attachés aux instances
def mounted_volumes(conn):
    instances = conn.compute.servers()
    volumes = conn.block_storage.volumes()
    instance_volumes = {}

    for volume in volumes:
        if volume.attachments:
            for attachment in volume.attachments:
                instance_id = attachment["server_id"]
                if instance_id not in instance_volumes:
                    instance_volumes[instance_id] = []
                instance_volumes[instance_id].append(volume)

    tree = {}
    for instance in instances:
        instance_id = instance.id
        instance_name = instance.name
        if instance_id in instance_volumes:
            tree[instance_name] = [
                volume.name for volume in instance_volumes[instance_id]
            ]
        else:
            tree[instance_name] = []

    return tree


# Afficher l'arborescence
def print_tree(tree_data):
    lang = get_language_preference()
    tree = Tree(TRANSLATIONS[lang]["mounted_volumes"])
    for instance, volumes in tree_data.items():
        instance_branch = tree.add(f"🖥️ {instance}")
        if volumes:
            for volume in volumes:
                instance_branch.add(f"💾 {volume}")
        else:
            instance_branch.add(TRANSLATIONS[lang]["no_volume_mounted"])
    console.print(tree)


# Lister les IP flottantes
def list_floating_ips(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["floating_ips_header"])
    floating_ips = list(conn.network.ips())

    if not floating_ips:
        print(TRANSLATIONS[lang]["no_floating_ips"])
        return

    table = Table(title="")
    table.add_column("ID", style="magenta")
    table.add_column("IP", style="cyan")
    table.add_column("Statut", style="green")
    for ip in floating_ips:
        table.add_row(ip.id, ip.floating_ip_address, ip.status)
    console.print(table)


# Lister les containers
def list_containers(conn):
    lang = get_language_preference()
    print_header(TRANSLATIONS[lang]["containers_header"])
    containers = list(conn.object_store.containers())

    if not containers:
        print(TRANSLATIONS[lang]["no_containers"])
        return

    table = Table(title="")
    table.add_column("Nom", style="cyan")
    table.add_column("Taille totale", justify="right", style="magenta")
    for container in containers:
        size_formatted = format_size(container.bytes)
        table.add_row(container.name, size_formatted)
    console.print(table)


# Fonction principale
def main():
    lang = get_language_preference()
    toolbox_version = get_version()
    print(
        f"[yellow bold]{TRANSLATIONS[lang]['welcome'].format(toolbox_version)}[/yellow bold]"
    )

    header = r"""
  ___                       _             _
 / _ \ _ __   ___ _ __  ___| |_ __ _  ___| | __
| | | | '_ \ / _ \ '_ \/ __| __/ _` |/ __| |/ /
| |_| | |_) |  __/ | | \__ \ || (_| | (__|   <
 \___/| .__/ \___|_| |_|___/\__\__,_|\___|_|\_\
/ ___||_|  _ _ __ ___  _ __ ___   __ _ _ __ _   _
\___ \| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |
 ___) | |_| | | | | | | | | | | | (_| | |  | |_| |
|____/ \__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |
                                            |___/
            By Loutre

    """

    print(header)

    # Test des credentials
    creds = load_openstack_credentials()
    if not creds:
        print(f"[bold red]{TRANSLATIONS[lang]['missing_vars']}[/bold red]")
        return

    conn = connection.Connection(**creds)
    if not conn.authorize():
        print("[bold red]❌ Échec de la connexion à OpenStack[/bold red]")
        return

    # Générer le fichier de billing
    billing_text = generate_billing()
    if "introuvable" in billing_text:
        print("[bold red]❌ Échec de la récupération du billing[/bold red]")
    else:
        try:
            json.loads(billing_text)
        except json.JSONDecodeError:
            print("[bold red]❌ Erreur de parsing du fichier billing[/bold red]")

    # Lister les ressources
    list_images(conn)
    list_instances(conn)
    list_snapshots(conn)
    list_backups(conn)
    list_volumes(conn)
    print_header(TRANSLATIONS[lang]["volumes_tree_header"])
    tree = mounted_volumes(conn)
    print_tree(tree)
    list_floating_ips(conn)
    list_containers(conn)


if __name__ == "__main__":
    main()
