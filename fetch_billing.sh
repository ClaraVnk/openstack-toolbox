#!/bin/bash
source ~/openstack.sh          # adapte selon ton environnement
source ~/projects/openstack/bin/activate  # adapte selon ton venv

# Format ISO 8601 attendu
DATE_FORMAT="%Y-%m-%dT%H:%M:%S+00:00"

# Définir les dates par défaut (les 2 dernières heures)
DEFAULT_START=$(date -u -d "2 hours ago" +"$DATE_FORMAT")
DEFAULT_END=$(date -u +"$DATE_FORMAT")

echo "Entrez la période de facturation souhaitée (format ISO 8601, ex: 2025-05-18T14:00:00+00:00)"
read -p "Date de début [Défaut: $DEFAULT_START] : " START
read -p "Date de fin   [Défaut: $DEFAULT_END] : " END
read -p "Nom du fichier de sortie [Défaut: billing.json] : " FILE

# Appliquer les valeurs par défaut si vide
START=${START:-$DEFAULT_START}
END=${END:-$DEFAULT_END}
FILE=${FILE:-billing.json}

echo
echo "Récupération des données de facturation..."
echo "Période : $START → $END"
echo "Fichier : $FILE"
echo

openstack rating dataframes get -b "$START" -e "$END" -c Resources -f json > "$FILE"

if [ $? -eq 0 ]; then
    echo "✅ Données enregistrées dans '$FILE'"
else
    echo "❌ Échec de la récupération des données"
    cat "$FILE"
fi