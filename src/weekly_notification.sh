#!/bin/bash

# Générer le fichier de rapport
python3 openstack_optimization.py

# Exécuter le script weekly_notification_optimization
python3 weekly_notification_optimization.py

# Demander à l'utilisateur s'il souhaite configurer l'envoi hebdomadaire
echo "💌 Voulez-vous paramétrer l'envoi hebdomadaire d'un e-mail avec le résumé de la semaine ? (o/n)"
read reponse
if [[ "$reponse" == "o" || "$reponse" == "O" ]]; then
  # Créer une tâche cron
  ## Définir le chemin relatif
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  SCRIPT_PATH="$SCRIPT_DIR/weekly_notification_optimization.py"

  ## Ligne cron à ajouter
  CRON_LINE="0 8 * * 1 $SCRIPT_PATH"

  ## Vérifier si la ligne existe déjà
  if crontab -l 2>/dev/null | grep -F "$CRON_LINE" >/dev/null; then
    echo "ℹ️ La tâche cron existe déjà."
  else
    ### Ajouter la tâche cron
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

    ### Vérifier que l'ajout a réussi
    if crontab -l 2>/dev/null | grep -Fq "$CRON_LINE"; then
      echo "✅ Tâche cron ajoutée : vous recevrez un email tous les lundis à 8h."
    else
      echo "❌ Échec de l'ajout de la tâche cron."
    fi
  fi
else 
  echo "❌ Configuration annulée."
fi