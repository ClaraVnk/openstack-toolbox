#!/bin/bash
source ~/openstack.sh          # adapte selon ton environnement
source ~/projects/openstack/bin/activate  # adapte selon ton venv

# Fonction pour convertir une date simple en ISO 8601 UTC
convert_to_iso8601() {
    # Entrée : date sous la forme "YYYY-MM-DD HH:MM"
    # Sortie : "YYYY-MM-DDTHH:MM:00+00:00"
    date -u -d "$1" +"%Y-%m-%dT%H:%M:00+00:00"
}

# Définir les dates par défaut (les 2 dernières heures)
DEFAULT_START=$(date -u -d "2 hours ago" +"%Y-%m-%dT%H:%M:00+00:00")
DEFAULT_END=$(date -u +"%Y-%m-%dT%H:%M:00+00:00")

echo "Entrez la période de facturation souhaitée (format simplifié: YYYY-MM-DD HH:MM)"
read -p "Date de début [Défaut: $(date -u -d "2 hours ago" +"%Y-%m-%d %H:%M")]: " START_INPUT
read -p "Date de fin   [Défaut: $(date -u +"%Y-%m-%d %H:%M")]: " END_INPUT

START_INPUT=${START_INPUT:-$(date -u -d "2 hours ago" +"%Y-%m-%d %H:%M")}
END_INPUT=${END_INPUT:-$(date -u +"%Y-%m-%d %H:%M")}

START=$(convert_to_iso8601 "$START_INPUT")
END=$(convert_to_iso8601 "$END_INPUT")

# Nom de fichier fixe
FILE="billing.json"

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