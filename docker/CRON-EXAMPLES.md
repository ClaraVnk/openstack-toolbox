# ⏰ Exemples de configuration Cron

Guide pratique pour configurer les horaires des tâches automatisées.

## 📝 Format Cron

```
minute hour day month weekday
```

- **minute** : 0-59
- **hour** : 0-23 (format 24h)
- **day** : 1-31
- **month** : 1-12
- **weekday** : 0-7 (0 et 7 = dimanche, 1 = lundi, etc.)

## 🎯 Exemples courants

### Horaires quotidiens

```env
# Tous les jours à 6h00
CRON_DAILY_SUMMARY=0 6 * * *

# Tous les jours à 9h30
CRON_DAILY_SUMMARY=30 9 * * *

# Tous les jours à minuit
CRON_DAILY_SUMMARY=0 0 * * *

# Deux fois par jour (8h et 20h)
CRON_DAILY_SUMMARY=0 8,20 * * *

# Toutes les 6 heures
CRON_DAILY_SUMMARY=0 */6 * * *

# Toutes les heures
CRON_DAILY_SUMMARY=0 * * * *

# Toutes les 30 minutes
CRON_DAILY_SUMMARY=*/30 * * * *
```

### Horaires hebdomadaires

```env
# Lundi à 8h00
CRON_WEEKLY_REPORT=0 8 * * 1

# Vendredi à 17h00
CRON_WEEKLY_REPORT=0 17 * * 5

# Dimanche à 23h00
CRON_WEEKLY_REPORT=0 23 * * 0

# Tous les jours de semaine (lundi-vendredi) à 9h
CRON_WEEKLY_REPORT=0 9 * * 1-5

# Weekend (samedi et dimanche) à 10h
CRON_WEEKLY_REPORT=0 10 * * 6,0
```

### Horaires mensuels

```env
# Premier jour du mois à 8h
CRON_OPTIMIZATION=0 8 1 * *

# 15 de chaque mois à 12h
CRON_OPTIMIZATION=0 12 15 * *

# Dernier jour du mois (approximatif)
CRON_OPTIMIZATION=0 8 28-31 * *

# Tous les trimestres (janvier, avril, juillet, octobre)
CRON_OPTIMIZATION=0 8 1 1,4,7,10 *
```

## 🎨 Cas d'usage pratiques

### Environnement de production

```env
# Rapport hebdomadaire le lundi matin
CRON_WEEKLY_REPORT=0 8 * * 1

# Résumé quotidien tôt le matin
CRON_DAILY_SUMMARY=0 6 * * *

# Optimisation en milieu de journée
CRON_OPTIMIZATION=0 14 * * *
```

### Environnement de développement

```env
# Rapport de test le vendredi après-midi
CRON_WEEKLY_REPORT=0 16 * * 5

# Résumé fréquent pour tests
CRON_DAILY_SUMMARY=*/15 * * * *

# Optimisation toutes les 2 heures
CRON_OPTIMIZATION=0 */2 * * *
```

### Monitoring intensif

```env
# Rapport quotidien (pas hebdomadaire)
CRON_WEEKLY_REPORT=0 8 * * *

# Résumé toutes les 4 heures
CRON_DAILY_SUMMARY=0 */4 * * *

# Optimisation toutes les heures
CRON_OPTIMIZATION=0 * * * *
```

### Économie de ressources

```env
# Rapport une fois par mois
CRON_WEEKLY_REPORT=0 8 1 * *

# Résumé une fois par jour
CRON_DAILY_SUMMARY=0 9 * * *

# Optimisation une fois par semaine
CRON_OPTIMIZATION=0 10 * * 1
```

## 🔧 Configuration

1. Éditez votre fichier `.env` :

```env
CRON_WEEKLY_REPORT=0 8 * * 1
CRON_DAILY_SUMMARY=0 9 * * *
CRON_OPTIMIZATION=0 10 * * *
```

2. Redémarrez le container :

```bash
docker-compose restart
```

3. Vérifiez la configuration :

```bash
docker-compose logs | grep "Cron schedules configured"
```

## 🐛 Dépannage

### Voir les tâches cron configurées

```bash
docker exec openstack-toolbox crontab -l
```

### Voir les logs d'exécution

```bash
# Rapport hebdomadaire
docker exec openstack-toolbox tail -f /var/log/openstack-toolbox/weekly-notification.log

# Résumé quotidien
docker exec openstack-toolbox tail -f /var/log/openstack-toolbox/daily-summary.log

# Optimisation
docker exec openstack-toolbox tail -f /var/log/openstack-toolbox/optimization.log
```

### Tester une tâche manuellement

```bash
# Exécuter le rapport immédiatement
docker exec openstack-toolbox python -m src.weekly_notification_optimization

# Exécuter le résumé
docker exec openstack-toolbox python -m src.openstack_summary

# Exécuter l'optimisation
docker exec openstack-toolbox python -m src.openstack_optimization
```

## 📚 Ressources

- [Crontab Generator](https://crontab.guru/) - Outil en ligne pour générer des expressions cron
- [Cron Wikipedia](https://en.wikipedia.org/wiki/Cron) - Documentation complète

## 💡 Astuces

### Désactiver une tâche

Pour désactiver temporairement une tâche, commentez-la dans `.env` ou utilisez un horaire impossible :

```env
# Désactivé
# CRON_WEEKLY_REPORT=0 8 * * 1

# Ou horaire impossible (31 février)
CRON_WEEKLY_REPORT=0 0 31 2 *
```

### Timezone

N'oubliez pas que les horaires sont basés sur la timezone configurée :

```env
TZ=Europe/Paris
```

Pour changer de timezone :

```env
TZ=America/New_York
TZ=Asia/Tokyo
TZ=UTC
```

### Éviter les heures de pointe

Si votre infrastructure OpenStack est très sollicitée à certaines heures, évitez ces créneaux :

```env
# Éviter 9h-17h (heures de bureau)
CRON_OPTIMIZATION=0 6 * * *  # 6h du matin
```

### Espacer les tâches

Pour éviter de surcharger le système, espacez les tâches :

```env
CRON_WEEKLY_REPORT=0 8 * * 1   # 8h00
CRON_DAILY_SUMMARY=15 8 * * *  # 8h15
CRON_OPTIMIZATION=30 8 * * *   # 8h30
```
