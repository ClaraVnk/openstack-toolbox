# OpenStack SysAdmin Toolbox 🧰

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![Infomaniak](https://img.shields.io/badge/infomaniak-0098FF?style=for-the-badge&logo=infomaniak&logoColor=white) 
![OpenStack](https://img.shields.io/badge/OpenStack-%23f01742.svg?style=for-the-badge&logo=openstack&logoColor=white)

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
- [Acknowledgments](#acknowledgments)

---

## Disclaimer

This toolbox is configured to match Infomaniak's Public Cloud costs (EUR and CHF).  
You can reconfigure it to match your provider's pricing if needed.

---

## Getting Started

### 1. Setup your virtual environment

- Log in to your OpenStack environment.
- Activate your virtual environment:  
  ```bash
  source openstack-toolbox/bin/activate
  source ../openstack-rc  # Source your OpenStack credentials here
  ```

### 2. Easy mode installation

Install the toolbox globally with pip:

```bash
pip install openstack-toolbox
```

---

## Available Commands

### OpenStack Summary

Generates a detailed summary of your OpenStack environment: instances, costs, backups, images, volumes, etc.

```bash
openstack_summary
```

![OpenStack Summary Screenshot 1](https://raw.githubusercontent.com/ClaraVnk/openstack-toolbox/main/img/openstack_summary_1.png)
![OpenStack Summary Screenshot 2](https://raw.githubusercontent.com/ClaraVnk/openstack-toolbox/main/img/openstack_summary_2.png)

---

### OpenStack Optimization Report (Weekly)

Identifies underutilized resources like inactive instances and unused volumes, with cost analysis.

```bash
openstack_optimization
```

![OpenStack Optimization](https://raw.githubusercontent.com/ClaraVnk/openstack-toolbox/main/img/openstack_optimization.png)

---

### Optimization Email Notification (Weekly)

Sends the weekly optimization report by email. Requires SMTP configuration.

```bash
weekly_notification_optimization
```

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

- OpenStack admin summary (beta):  
  ```bash
  python3 openstack_admin_script.py
  ```

- OpenStack optimization:  
  ```bash
  python3 openstack_optimization.py
  ```

- Weekly notification (email):  
  ```bash
  python3 weekly_notification_optimization.py
  ```

---

## Acknowledgments

Special thanks to [@kallioli](https://github.com/kallioli) for his support!  
Thanks also to [@PAPAMICA](https://github.com/PAPAMICA) for his valuable suggestions.

---

If you have questions or want to contribute, feel free to open an issue or a pull request! Don't forget to star ⭐️ !