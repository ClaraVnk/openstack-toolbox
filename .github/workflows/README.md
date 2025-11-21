# GitHub Actions Workflows

## 🔄 Workflow disponible

### `build.yml` - Build et Publication

Déclenché sur :
- Push sur `main` ou `develop`
- Tags `v*` (ex: v1.4.0)
- Pull Requests vers `main`

**Actions** :
1. **Build Python Package**
   - Build le package Python
   - Vérifie avec twine
   - Upload les artifacts
   - 🚀 **Publie automatiquement sur PyPI** (push sur main)

2. **Build Docker Image**
   - Build l'image Docker multi-arch (amd64, arm64)
   - Push sur GitHub Container Registry
   - Tags automatiques selon le contexte
   - Cache optimisé

## 📦 Images Docker

Les images sont publiées sur GitHub Container Registry :

```
ghcr.io/claravnk/openstack-toolbox:latest
ghcr.io/claravnk/openstack-toolbox:v1.4.0
ghcr.io/claravnk/openstack-toolbox:main
```

### Utilisation

```bash
# Dernière version stable
docker pull ghcr.io/claravnk/openstack-toolbox:latest

# Version spécifique
docker pull ghcr.io/claravnk/openstack-toolbox:v1.4.0

# Branche main
docker pull ghcr.io/claravnk/openstack-toolbox:main
```

## 🔑 Secrets requis

### Pour PyPI (publication du package)

Créez un secret `PYPI_API_TOKEN` :

1. Allez sur https://pypi.org/manage/account/token/
2. Créez un nouveau token API
3. Dans GitHub : Settings → Secrets → Actions → New repository secret
4. Nom : `PYPI_API_TOKEN`
5. Valeur : votre token PyPI

### Pour GitHub Container Registry

Le secret `GITHUB_TOKEN` est automatiquement fourni par GitHub Actions.

## 🚀 Workflow de release

### 1. Mettre à jour la version

```bash
# Dans pyproject.toml
version = "1.5.0"
```

### 2. Commit et tag

```bash
git add pyproject.toml
git commit -m "chore: bump version to 1.5.0"
git tag v1.5.0
git push origin main --tags
```

### 3. Automatique

GitHub Actions va :
- ✅ Build le package Python
- ✅ Publier sur PyPI
- ✅ Build l'image Docker
- ✅ Publier sur ghcr.io avec les tags :
  - `v1.5.0`
  - `1.5`
  - `1`
  - `latest`

## 📊 Statut du workflow

Le badge est déjà ajouté au README principal :

```markdown
![Build](https://github.com/ClaraVnk/openstack-toolbox/workflows/Build%20and%20Publish/badge.svg)
```

## 🔧 Personnalisation

### Changer les branches surveillées

Éditez `on.push.branches` dans les workflows :

```yaml
on:
  push:
    branches:
      - main
      - staging  # Ajouter d'autres branches
```

### Désactiver la publication PyPI

Commentez ou supprimez la step "Publish to PyPI" dans `build.yml`.

### Changer le registry Docker

Modifiez `env.REGISTRY` dans `build.yml` :

```yaml
env:
  REGISTRY: docker.io  # Pour Docker Hub
  IMAGE_NAME: username/openstack-toolbox
```

## 🐛 Dépannage

### Le build Docker échoue

Vérifiez que le `Dockerfile` est valide :

```bash
docker build -t test .
```

### La publication PyPI échoue

- Vérifiez que le token est correct
- Vérifiez que la version n'existe pas déjà sur PyPI
- Vérifiez le format du package avec `twine check dist/*`

### Les permissions GitHub Container Registry

Assurez-vous que les packages GitHub sont publics :
- Settings → Packages → Change visibility → Public
