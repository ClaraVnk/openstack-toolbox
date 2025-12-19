# OpenStack Toolbox 🧰

![Build](https://github.com/ClaraVnk/openstack-toolbox/workflows/Build%20and%20Publish%20Docker/badge.svg)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Infomaniak](https://img.shields.io/badge/infomaniak-0098FF?style=for-the-badge&logo=infomaniak&logoColor=white)
![OpenStack](https://img.shields.io/badge/OpenStack-%23f01742.svg?style=for-the-badge&logo=openstack&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=Prometheus&logoColor=white)

A suite of tools to optimize and manage your OpenStack resources, with multilingual support (FR/EN).

> **Version 1.6.1** - Code quality improvements, security enhancements, and better reliability!

## ✨ What's New in v1.6.1

- 🔒 **HTTP timeout protection** - All HTTP requests now have 30s timeout to prevent indefinite hangs
- 🧹 **Code quality** - Formatted with Black and isort, cleaned unused imports
- 🔧 **Bug fixes** - Fixed relative imports and credential loading issues
- ✅ **Security audit** - Passed Bandit security scan with 0 critical issues
- 📝 **Type safety** - Corrected type hints for better IDE support

## 📜 Previous Versions

### v1.6.0
- 🔒 **Encrypted SMTP passwords** - Passwords are now encrypted using Fernet (AES-128)
- 📊 **Professional logging** - Colored console output, automatic rotation, JSON support
- 📝 **Complete type hints** - Better IDE support and code quality
- 🔧 **Specific exceptions** - 12 custom exceptions for better error handling
- 📁 **Organized structure** - Clean separation of code and documentation

## 📋 Features

### Core Tools

- 📊 **Metrics Collector** - Real-time Gnocchi metrics with Prometheus export
- 📈 **Resource Summary** - Complete overview of instances, volumes, snapshots, and costs
- 👨‍💼 **Administration** - Multi-project management and resource overview
- 📧 **Weekly Notifications** - Automated email reports with secure SMTP
- 🔍 **Optimization** - Identify underutilized resources

### New in v1.6.0

- 🔒 **Security Module** (`src/security.py`) - Encryption/decryption for sensitive data
- 📊 **Logger Module** (`src/logger.py`) - Professional logging with rotation and colors
- 🔧 **Exceptions Module** (`src/exceptions.py`) - 12 specific exceptions for better error handling
- 📝 **Type Hints** - Complete type annotations for better IDE support

## 🛠️ Installation

### 🐳 Docker (Recommended)

Docker deployment includes **all features**: Prometheus metrics collector + automated cron tasks (weekly reports, daily summaries, optimization).

#### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/openstack-toolbox.git
cd openstack-toolbox

# Configure credentials
cp .env.example .env
nano .env

# Start the complete suite
docker-compose up -d
```

#### What's Included

- ✅ **Prometheus metrics** on port 8000 (real-time)
- ✅ **Automated cron tasks**:
  - Weekly report (Monday 8:00 AM)
  - Daily summary (9:00 AM)
  - Optimization analysis (10:00 AM)
- ✅ **Email notifications** (if SMTP configured)
- ✅ **Centralized logs** in `./logs/`
- ✅ **Auto-restart** on failure

#### Configuration

Edit `.env` file with your credentials:

```env
# OpenStack (required)
OS_AUTH_URL=https://api.pub1.infomaniak.cloud:5000/v3
OS_PROJECT_NAME=your-project
OS_USERNAME=your-username
OS_PASSWORD=your-password
OS_USER_DOMAIN_NAME=default
OS_PROJECT_DOMAIN_NAME=default
OS_REGION_NAME=RegionOne

# SMTP (optional, for email notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_TO_EMAIL=recipient@example.com

# Timezone
TZ=Europe/Paris
```

**Note for Gmail:** Use an [app password](https://support.google.com/accounts/answer/185833), not your regular password.

#### Useful Commands

```bash
# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart
docker-compose restart

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Execute commands manually
docker exec openstack-toolbox python -m src.openstack_summary
docker exec openstack-toolbox python -m src.openstack_optimization

# View cron jobs
docker exec openstack-toolbox crontab -l

# View specific logs
docker exec openstack-toolbox tail -f /var/log/openstack-toolbox/weekly-notification.log
```

#### Customize Cron Schedules

You can easily customize when tasks run by setting environment variables in your `.env` file:

```env
# Cron format: minute hour day month weekday
CRON_WEEKLY_REPORT=0 8 * * 1      # Monday at 8:00 AM (default)
CRON_DAILY_SUMMARY=0 9 * * *      # Every day at 9:00 AM (default)
CRON_OPTIMIZATION=0 10 * * *      # Every day at 10:00 AM (default)
```

**Common examples:**

```env
# Weekly report on Friday at 5:00 PM
CRON_WEEKLY_REPORT=0 17 * * 5

# Daily summary at 6:00 AM
CRON_DAILY_SUMMARY=0 6 * * *

# Optimization every 6 hours
CRON_OPTIMIZATION=0 */6 * * *

# Run every 30 minutes
CRON_OPTIMIZATION=*/30 * * * *

# Multiple times per day (8 AM and 8 PM)
CRON_DAILY_SUMMARY=0 8,20 * * *
```

**Cron format reference:**
- `*` = every
- `*/N` = every N units
- `N,M` = at N and M
- `N-M` = from N to M

| Field | Values | Examples |
|-------|--------|----------|
| Minute | 0-59 | `0`, `*/15`, `30` |
| Hour | 0-23 | `8`, `*/6`, `9,17` |
| Day | 1-31 | `1`, `15`, `*/2` |
| Month | 1-12 | `*`, `1,6,12` |
| Weekday | 0-7 (0=Sunday) | `1` (Monday), `1-5` (weekdays) |

After changing schedules, restart the container:

```bash
docker-compose restart
```

#### Integration with Prometheus

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'openstack-toolbox'
    static_configs:
      - targets: ['openstack-toolbox:8000']
    scrape_interval: 60s
    scrape_timeout: 30s
```

#### Complete Stack with Grafana

Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus.yml.example:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - monitoring

volumes:
  prometheus-data:
  grafana-data:
```

Start everything: `docker-compose up -d`

#### Troubleshooting

**Container won't start:**
```bash
docker-compose logs
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

**Metrics not available:**
```bash
curl http://localhost:8000/metrics
docker-compose logs | grep -i error
```

**Cron tasks not running:**
```bash
docker exec openstack-toolbox ps aux | grep cron
docker exec openstack-toolbox crontab -l
docker exec openstack-toolbox service cron status
```

**Email not sent:**
```bash
docker exec openstack-toolbox env | grep SMTP
docker exec openstack-toolbox tail -f /var/log/openstack-toolbox/weekly-notification.log
```

### 💻 From source (for development)

```bash
git clone https://github.com/your-username/openstack-toolbox.git
cd openstack-toolbox

# Install in development mode
pip install -e .

# Or use directly with Docker
docker-compose up -d
```

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

### With Docker (Recommended)

Once the container is running with `docker-compose up -d`, everything runs automatically:

- **Metrics Collector** runs continuously on port 8000
- **Cron tasks** execute automatically:
  - Weekly report: Monday 8:00 AM
  - Daily summary: Every day 9:00 AM
  - Optimization: Every day 10:00 AM

#### Execute Commands Manually

```bash
# Resource summary
docker exec openstack-toolbox python -m src.openstack_summary

# Optimization analysis
docker exec openstack-toolbox python -m src.openstack_optimization

# Send weekly notification
docker exec openstack-toolbox python -m src.weekly_notification_optimization

# View metrics
curl http://localhost:8000/metrics
```

### With Python (Development)

If you installed from source:

```bash
# Metrics collector
openstack-metrics-collector

# Resource summary
openstack-summary

# Administration
openstack-admin

# Weekly notifications
weekly-notification
```

### Available Metrics

The collector exposes these metrics on port 8000:
- `openstack_identity_metrics` - Identity service metrics
- `openstack_compute_metrics` - Compute (instances) metrics
- `openstack_block_storage_metrics` - Block storage (volumes) metrics
- `openstack_network_metrics` - Network metrics
- `openstack_gnocchi_metric` - Gnocchi telemetry metrics

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

## 📁 Project Structure

```
openstack-toolbox/
├── src/          # Python source code (12 modules)
└── .github/      # GitHub Actions CI/CD
```

### Source Code (`src/`)

**Core Modules:**
- `openstack_toolbox.py` - Main CLI
- `openstack_summary.py` - Resource summary
- `openstack_admin.py` - Administration tools
- `openstack_metrics_collector.py` - Prometheus exporter
- `openstack_optimization.py` - Resource optimization
- `weekly_notification_optimization.py` - Email notifications

**Utility Modules (v1.6.0):**
- `config.py` - Configuration management
- `security.py` - Encryption/decryption ✨ NEW
- `logger.py` - Logging system ✨ NEW
- `exceptions.py` - Custom exceptions ✨ NEW
- `utils.py` - Helper functions

## � Migration from v1.5.0

### Automatic Migration

- ✅ **100% backward compatible** - No action required
- ✅ Existing SMTP configurations continue to work
- ✅ System will prompt to re-encrypt passwords on next use

### Recommended Actions

```bash
# Reconfigure SMTP to enable encryption
weekly-notification
```

### New Dependencies

```bash
# Install the new security dependency
pip install cryptography>=41.0.0
```

### Security Improvements

Configuration files now have restricted permissions:
- `~/.config/openstack-toolbox/smtp_config.ini` : 600 (rw-------)
- `~/.config/openstack-toolbox/.encryption_key` : 600 (rw-------)

### Troubleshooting

If you encounter decryption errors:

```bash
# Remove old configuration
rm ~/.config/openstack-toolbox/smtp_config.ini
rm ~/.config/openstack-toolbox/.encryption_key

# Reconfigure
weekly-notification
```

## 📝 Changelog

### [1.6.1] - 2024-12-19

**Fixed:**
- 🔧 Fixed relative imports in all modules (from `src.` to `.`)
- 🔧 Fixed credential loading to properly handle tuple return values
- 🔧 Corrected type hint `any` to `Any` in config.py

**Improved:**
- 🔒 Added 30-second timeout to all HTTP requests (prevents hanging)
- 🧹 Removed unused imports and variables
- 🧹 Cleaned whitespace in blank lines
- ✨ Code formatted with Black (line-length=120)
- ✨ Imports sorted with isort (profile=black)

**Security:**
- ✅ Passed Bandit security audit with 0 medium/high severity issues
- 🔒 All HTTP requests now protected against indefinite hangs

**No breaking changes** - Full backward compatibility maintained

### [1.6.0] - 2024-11-21

**Added:**
- 🔒 Encrypted SMTP passwords using Fernet (AES-128)
- 📊 Professional logging with rotation and colors
- 🔧 12 custom exceptions for better error handling
- 📝 Complete type hints on all core modules
- 📁 Organized project structure

**Security:**
- Encrypted password storage
- Restricted file permissions (600)
- Unique encryption key per installation

**No breaking changes** - Full backward compatibility maintained

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the project
2. Create a branch (`git checkout -b feature/improvement`)
3. Commit (`git commit -am 'Add feature'`)
4. Push (`git push origin feature/improvement`)
5. Open a Pull Request

See [docs/IMPROVEMENTS.md](docs/IMPROVEMENTS.md) for technical details.

## ✨ Credits

Special thanks to [Kevin Allioli](https://github.com/kallioli), Cloud Architect & SysAdmin, for his valuable contributions and expertise in OpenStack development.

## 📝 License

This project is under Apache License 2.0. See `LICENSE.TXT` file for more details.

## ✨ Author

Developed by Loutre