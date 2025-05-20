import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup-cron', action='store_true', help="Ajoute une tâche cron pour lancer ce script chaque lundi à 8h.")
    args = parser.parse_args()

    if args.setup_cron:
        setup_cron()
        return

def setup_cron():
    """Ajoute ce script à la crontab pour une exécution automatique chaque lundi à 8h."""
    python_exe = sys.executable
    script_path = os.path.abspath(__file__)
    cron_line = f"0 8 * * 1 {python_exe} {script_path} > /dev/null 2>&1\n"

    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    existing_cron = result.stdout if result.returncode == 0 else ""

    if cron_line.strip() in existing_cron:
        print("✅ La tâche cron est déjà configurée.")
        return

    new_cron = existing_cron + cron_line
    proc = subprocess.run(['crontab', '-'], input=new_cron, text=True)
    if proc.returncode == 0:
        print("✅ Tâche cron ajoutée : le script s'exécutera tous les lundis à 8h.")
    else:
        print("❌ Échec lors de l'ajout à la crontab.")