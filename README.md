# OpenStack Toolbox 🧰
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&logo=pypi&logoColor=1f73b7)
![Infomaniak](https://img.shields.io/badge/infomaniak-0098FF?style=for-the-badge&logo=infomaniak&logoColor=white) 
![OpenStack](https://img.shields.io/badge/OpenStack-%23f01742.svg?style=for-the-badge&logo=openstack&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=Prometheus&logoColor=white)

A suite of tools to optimize and manage your OpenStack resources, with multilingual support (FR/EN).

## 📋 Features

- 📊 **Metrics Collector** (`openstack_metrics_collector.py`)
  - Real-time Gnocchi metrics
  - Prometheus export
  - Request parallelization
  - Multi-project support

- 📈 **Resource Summary** (`openstack_summary.py`)
  - Instance list and details
  - Volumes and snapshots
  - Images and containers
  - Cost estimation (calibrated for Infomaniak pricing in EUR/CHF)
  - Mounted volumes tree view

- 👨‍💼 **Administration** (`openstack_admin.py`)
  - Project management
  - Resource overview
  - Operation parallelization

- 📧 **Weekly Notifications** (`weekly_notification_optimization.py`)
  - Automated email reports
  - Interactive SMTP configuration
  - Cron scheduling

## 🛠️ Installation

You can install the toolbox in two ways:

### From PyPI (recommended)
```bash
pip install openstack-toolbox
```

### From source
```bash
git clone https://github.com/your-username/openstack-toolbox.git
cd openstack-toolbox
pip install
```

Dependencies will be automatically managed through `pyproject.toml`.

## ⚙️ Configuration

### OpenStack Environment Variables

The toolbox supports two methods for configuring OpenStack credentials:

1. Using environment variables directly:
```bash
export OS_AUTH_URL=https://your-auth-url
export OS_PROJECT_NAME=your-project
export OS_USERNAME=your-username
export OS_PASSWORD=your-password
export OS_USER_DOMAIN_NAME=your-domain
export OS_PROJECT_DOMAIN_NAME=your-project-domain
export OS_REGION_NAME=your-region
```

2. Using a `.env` file at the project root:
```bash
OS_AUTH_URL=https://your-auth-url
OS_PROJECT_NAME=your-project
OS_USERNAME=your-username
OS_PASSWORD=your-password
OS_USER_DOMAIN_NAME=your-domain
OS_PROJECT_DOMAIN_NAME=your-project-domain
OS_REGION_NAME=your-region
```

Choose the method that best suits your workflow. The toolbox will automatically detect and use the credentials from either source.

### SMTP Configuration (for notifications)

SMTP configuration is interactive. Run:
```bash
weekly-notification
```

The script will guide you to configure:
- SMTP Server
- Port
- Credentials
- Email addresses

## 🚀 Usage

### Metrics Collector

```bash
openstack-metrics-collector
```

The collector implements a passive Prometheus exporter that starts a server on port 8000. Metrics are stored in a custom directory and served on demand when Prometheus scrapes them.

Available metrics:
- `openstack_identity_metrics`
- `openstack_compute_metrics`
- `openstack_block_storage_metrics`
- `openstack_network_metrics`
- `openstack_gnocchi_metric`

All metrics are stored in `/var/lib/openstack-metrics-collector/` by default. You can customize this path in the configuration.

#### Prometheus Configuration

Add this job to your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'openstack'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
    scrape_interval: 30s
```

This will collect OpenStack metrics every 30 seconds. Adjust the `scrape_interval` and `targets` according to your needs.

#### Alerting Rules

Create an `alert.yml` file with these example rules:
```yaml
groups:
- name: openstack_alerts
  rules:
  - alert: OpenStackInstanceDown
    expr: openstack_instance_status == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Instance {{ $labels.instance_name }} is down"
      description: "Instance {{ $labels.instance_name }} in project {{ $labels.project_name }} has been down for more than 5 minutes"

  - alert: OpenStackHighCPUUsage
    expr: openstack_instance_cpu_usage > 90
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage on {{ $labels.instance_name }}"
      description: "Instance {{ $labels.instance_name }} has had CPU usage above 90% for 15 minutes"

  - alert: OpenStackLowDiskSpace
    expr: openstack_volume_free_space / openstack_volume_total_space * 100 < 10
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Low disk space on volume {{ $labels.volume_name }}"
      description: "Volume {{ $labels.volume_name }} has less than 10% free space"
```

Add this file to your Prometheus configuration to enable alerting on common OpenStack issues.

### Resource Summary

```bash
openstack-summary
```

Displays a complete summary of your OpenStack resources:
- Instances (CPU, RAM, disk)
- Volumes and snapshots
- Images and containers
- Estimated costs (specific to Infomaniak hosting provider, in EUR and CHF)

### Administration

```bash
openstack-admin
```

Enter the project ID to view:
- Project details
- Resource list
- Usage metrics

### Weekly Notifications

```bash
weekly-notification
```

Configures and sends weekly reports via email.

## 🌍 Internationalization

The project supports French (default) and English.
To change the language, use:

```bash
openstack-toolbox --config
```

This will display an interactive menu to select your preferred language. The choice will be saved and used across all tools in the suite.

You can also view all available commands in your preferred language with:

```bash
openstack-toolbox
```

## 📚 Function Documentation

### Utils (`utils.py`)

- `format_size(size_bytes)`: Formats a size in bytes
- `parse_flavor_name(name)`: Parses an OpenStack flavor name
- `isoformat(dt)`: Converts a date to ISO 8601
- `print_header(header)`: Displays a formatted header

### Config (`config.py`)

- `get_language_preference()`: Gets the configured language
- `set_language_preference(lang)`: Sets the language
- `create_smtp_config_interactive()`: Configures SMTP
- `load_smtp_config()`: Loads SMTP config
- `load_openstack_credentials()`: Loads OpenStack credentials

### Metrics (`openstack_metrics_collector.py`)

- Class `GnocchiAPI`: Client for Gnocchi API
  - `get_resources()`
  - `get_metrics_for_resource()`
  - `get_measures()`
- `collect_resource_metrics()`: Per-resource collection
- `collect_gnocchi_metrics_parallel()`: Parallel collection

### Admin (`openstack_admin.py`)

- `process_resource_parallel()`: Parallel processing
- `list_all_resources()`: Lists all resources
- Specialized listing functions for each type

### Notifications (`weekly_notification_optimization.py`)

- `generate_report()`: Generates the report
- `send_email()`: Sends via SMTP
- `setup_cron()`: Configures cron task

## 🤝 Contributing

Contributions are welcome! Feel free to:
1. Fork the project
2. Create a branch (`git checkout -b feature/improvement`)
3. Commit (`git commit -am 'Add feature'`)
4. Push (`git push origin feature/improvement`)
5. Open a Pull Request

## ✨ Credits

Special thanks to [Kevin Allioli](https://github.com/kallioli), Cloud Architect & SysAdmin, for his valuable contributions and expertise in OpenStack development.

## 📝 License

This project is under Apache License 2.0. See `LICENSE.TXT` file for more details.

## ✨ Author

Developed by Loutre