import subprocess
import sys

def run_script(script_path):
    print(f"Lancement de {script_path} ...")
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Erreur lors de l'exécution de {script_path} :")
        print(result.stderr)
        sys.exit(result.returncode)
    print(f"{script_path} terminé avec succès.\n")

    def main():
    run_script('weekly_billing.py')
    run_script('openstack_optimization.py')
    run_script('notification.py')

    main()