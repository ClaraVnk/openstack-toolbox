#!/usr/bin/env python3
import subprocess
import sys
import os
import importlib
import tomllib  # Python 3.11+
from pathlib import Path

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    importlib.import_module('rich')
except ImportError:
    print("[yellow]⚙️ Installation du package rich...[/]")
    install_package('rich')

from rich import print

def get_version():
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

def run_script(script_name, arg=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))  # = src/
    script_path = os.path.join(script_dir, script_name)

    cmd = [sys.executable, script_path]
    if arg:
        cmd.append(arg)

    result = subprocess.run(cmd, check=True)
    if result.returncode != 0:
        print(f"[bold red]❌ Le script {script_name} a échoué avec le code {result.returncode}[/]")
        sys.exit(result.returncode)

def main():
    version = get_version()
    print(f"\n[bold yellow]🎉 Bienvenue dans OpenStack Toolbox v{version} 🎉[/]")
    print("[cyan]Commandes disponibles :[/]")
    print("  • [bold]openstack_summary[/]        → Génère un résumé global du projet")
    print("  • [bold]openstack_optimization[/]   → Identifie les ressources sous-utilisées dans la semaine")
    print("  • [bold]openstack_weekly_notification[/]   → Paramètre l'envoi d'un e-mail avec le résumé de la semaine")

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
    print(f"[bold blue]{header}[/]")
    run_script("fetch_billing.py")
    billing_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'billing.json')
    run_script("openstack_script.py", billing_file)

if __name__ == "__main__":
    main()