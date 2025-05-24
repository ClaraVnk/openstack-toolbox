# OpenStack Toolbox 🧰

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&logo=pypi&logoColor=1f73b7)
![Infomaniak](https://img.shields.io/badge/infomaniak-0098FF?style=for-the-badge&logo=infomaniak&logoColor=white) 
![OpenStack](https://img.shields.io/badge/OpenStack-%23f01742.svg?style=for-the-badge&logo=openstack&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=Prometheus&logoColor=white)

---

## Table of Contents

- [Disclaimer](#disclaimer)
- [Getting Started](#getting-started)
- [Available Commands](#available-commands)
  - [OpenStack Summary](#openstack-summary)
  - [OpenStack Optimization Report (Weekly)](#openstack-optimization-report-weekly)
  - [Optimization Email Notification (Weekly)](#optimization-email-notification-weekly)
- [Important Note: SMTP Configuration with Gmail](#important-note-smtp-configuration-with-gmail)
- [Manual Mode](#manual-mode)
- [Export OpenStack Metrics to Prometheus](#export-openstack-metrics-to-prometheus)
- [Acknowledgments](#acknowledgments)

---

## Disclaimer

This toolbox is configured to match Infomaniak's Public Cloud costs (EUR and CHF).  
You can reconfigure it to match your provider's pricing if needed.

---

## Getting Started

### 1. Setup your virtual environment

- Activate your virtual environment 
  ```bash
  source openstack-toolbox/bin/activate
  ```
- Source your credentials
  ```
  source ../openstack-rc  
  ```

### 2. Easy mode installation

Install the toolbox globally with pip:

```bash
pip install openstack-toolbox
```

```bash
pip install .
```

---

## Available Commands

```bash
openstack-toolbox
```

Resume all the available commands.

[![openstack-toolbox.png](https://github.com/ClaraVnk/docs/raw/main/openstack-toolbox.png)](https://github.com/ClaraVnk/docs/blob/main/openstack-toolbox.png)  

### OpenStack Summary

Generates a detailed summary of your OpenStack environment: instances, costs, backups, images, volumes, etc.

```bash
openstack-summary
```

[![openstack-summary-1.png](https://github.com/ClaraVnk/docs/raw/main/openstack-summary-1.png)](https://github.com/ClaraVnk/docs/blob/main/openstack-summary-1.png)  
[![openstack-summary-2.png](https://github.com/ClaraVnk/docs/raw/main/openstack-summary-2.png)](https://github.com/ClaraVnk/docs/blob/main/openstack-summary-2.png)  
[![openstack-summary-3.png](https://github.com/ClaraVnk/docs/raw/main/openstack-summary-3.png)](https://github.com/ClaraVnk/docs/blob/main/openstack-summary-3.png)  

---

### Openstack Admin mode

Maybe, as a SysAdmin, you don't want the billing but you need to focus on a special project ID:
```bash
openstack-admin
```

[![openstack-admin.png](https://github.com/ClaraVnk/docs/raw/main/openstack-admin.png)](https://github.com/ClaraVnk/docs/blob/main/openstack-admin.png)  

---

### OpenStack Optimization Report (Weekly)

Identifies underutilized resources like inactive instances and unused volumes, with cost analysis.

```bash
openstack-optimization
```

[![openstack-optimization.png](https://github.com/ClaraVnk/docs/raw/main/openstack-optimization.png)](https://github.com/ClaraVnk/docs/blob/main/openstack-optimization.png)  

---

### Optimization Email Notification (Weekly)

Sends the weekly optimization report by email. Requires SMTP configuration.

```bash
weekly-notification
```

[![weekly_notification.png](https://github.com/ClaraVnk/docs/raw/main/weekly_notification.png)](https://github.com/ClaraVnk/docs/blob/main/weekly_notification.png)  

---

## Important Note: SMTP Configuration with Gmail

Google now requires secure authentication via **OAuth 2.0** or the use of an **App Password** (if two-step verification is enabled) for SMTP access.

⚠️ **Without this, email sending will fail.**

- For detailed info, visit the official Google guide:  
  https://support.google.com/accounts/answer/185833

- To create an App Password, follow this guide:  
  https://support.google.com/accounts/answer/185833#app-passwords

**Tip:** Enable two-step verification and create an App Password to use Gmail SMTP with this project.

---

## Manual Mode

If you prefer manual setup or want to contribute:

### Clone the repository

```bash
git clone https://github.com/ClaraVnk/openstack-toolbox.git
cd openstack-toolbox/src
```

### Run scripts manually

- OpenStack summary:  
  ```bash
  python3 openstack_summary.py
  ```

- OpenStack admin summary:  
  ```bash
  python3 openstack_admin.py
  ```

- OpenStack optimization:  
  ```bash
  python3 openstack_optimization.py
  ```

- Weekly notification (email):  
  ```bash
  python3 weekly_notification_optimization.py
  ```

- Metrics exporter:
  ```bash
  python3 openstack_metrics_collector.py
  ```

---

## Export OpenStack Metrics to Prometheus

This toolbox integrates with an optional Prometheus exporter script to expose OpenStack metrics.

### Features

- Collects data from:
  - Identity (Keystone)
  - Compute (Nova)
  - Used Images (Glance)
  - Block Storage (Cinder)
  - Network (Neutron)
  - Object Storage (Swift)
  - Quotas (Compute or Identity)
  - Gnocchi metrics (via REST API)
- Exposes a `/metrics` endpoint compatible with Prometheus
- Supports multiple projects
- Configurable via `.env` file

### Running the exporter

```bash
openstack-metrics-exporter
```

The exporter exposes metrics at: `http://localhost:8000/metrics`

### Prometheus scrape config

Ensure Prometheus is configured to scrape the metrics from the endpoint `/metrics` exposed by your script.

The Prometheus scraper will store the collected data in its configured data directory. If you're using a custom Prometheus setup, make sure that the `--storage.tsdb.path` option in your Prometheus configuration points to a persistent and appropriate directory. This is important to retain the metrics between restarts and for long-term analysis.

Example startup with a custom data path:

```bash
./prometheus --config.file=prometheus.yml --storage.tsdb.path=/data/prometheus
```

Add the following configuration to your `prometheus.yml` file:

```yaml
scrape_configs:
  - job_name: 'openstack-metrics'
    static_configs:
      - targets: ['localhost:8000']
```

### Example Prometheus alerts

Then create an `alerts.yml` file with the following content:

```yaml
groups:
  - name: exporter-alerts
    rules:
      - alert: ExporterTooManyErrors
        expr: exporter_errors_total > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Exporter has encountered too many errors"
      - alert: TooManyInstancesUsed
        expr: openstack_compute_instance_count{project_name="myproj"} / openstack_quota_metrics{resource="instances"} > 0.9
        annotations:
          summary: "Too many instances are used"
      - alert: HighCPUUsage
        expr: openstack_gnocchi_metric{metric_name="cpu"} > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High CPU usage detected on an OpenStack resource"
```

### Logs

The exporter writes logs to a file named `openstack-metrics.log` in the directory where you run the script. Logs are formatted in JSON to facilitate parsing and integration with log management tools.

By default, the log file is created in the current working directory:

```bash
./openstack-metrics.log
```

To monitor logs in real time, use:
```bash
tail -f openstack-metrics.log
```

---

## Acknowledgments

Special thanks to [@kallioli](https://github.com/kallioli) for his support!  
Thanks also to [@PAPAMICA](https://github.com/PAPAMICA) for his valuable suggestions.

---

If you have questions or want to contribute, feel free to open an issue or a pull request! Don't forget to star ⭐️ !