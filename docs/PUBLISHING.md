# Publishing to PyPI

This document describes how to publish `robotframework-tracer` to PyPI.

## Prerequisites

### 1. PyPI Account Setup

1. Register at https://pypi.org/account/register/
2. Verify your email address
3. Enable 2FA (required for new projects)

### 2. Create API Token

1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `robotframework-tracer`
4. Scope: "Entire account" (for first upload)
5. Save the token securely (starts with `pypi-`)

### 3. Add Token to GitHub Secrets

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `PYPI_TOKEN`
4. Value: Your PyPI API token (the full `pypi-...` string)
5. Click "Add secret"

## Manual Publishing

### First Time Setup

```bash
pip install build twine
```

### Build and Upload

```bash
# Build distribution packages
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: Your PyPI API token

### Test on TestPyPI First (Recommended)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ robotframework-tracer
```

## Automated Publishing (GitHub Actions)

The repository includes a GitHub Actions workflow (`.github/workflows/publish.yml`) that automatically publishes to PyPI when you create a GitHub release.

### How It Works

1. Create a new release on GitHub
2. GitHub Actions automatically:
   - Builds the package
   - Uploads to PyPI using the `PYPI_TOKEN` secret
3. Package is available on PyPI within minutes

### Release Process

```bash
# 1. Update version in src/robotframework_tracer/version.py
VERSION = "0.2.0"

# 2. Update CHANGELOG.md with release notes

# 3. Commit and push
git add .
git commit -m "Bump version to 0.2.0"
git push

# 4. Create and push tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# 5. Create GitHub release
gh release create v0.2.0 --title "v0.2.0" --notes "Release notes here"
```

The workflow will automatically publish to PyPI.

## After First Upload

After the first successful upload, you can create a project-scoped token:

1. Go to https://pypi.org/manage/project/robotframework-tracer/settings/
2. Create a new API token with scope: "Project: robotframework-tracer"
3. Update the `PYPI_TOKEN` secret in GitHub

## Troubleshooting

### Package name already taken
If `robotframework-tracer` is taken, choose a different name and update:
- `pyproject.toml` → `name` field
- `setup.py` → `name` parameter
- README.md installation instructions

### Version already exists
You cannot re-upload the same version. Increment the version number in `src/robotframework_tracer/version.py`.

### Authentication failed
- Ensure username is `__token__` (not your PyPI username)
- Verify the token starts with `pypi-`
- Check token hasn't expired or been revoked

### Build errors
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Rebuild
python -m build
```

## Verification

After publishing, verify the package:

```bash
# Install from PyPI
pip install robotframework-tracer

# Test basic functionality
python -c "from robotframework_tracer import TracingListener; print('OK')"

# Check version
pip show robotframework-tracer
```

## Package Metadata

The package metadata is defined in `pyproject.toml`:
- Name: `robotframework-tracer`
- Description: From README.md
- License: Apache-2.0
- Python version: >=3.8
- Dependencies: Listed in `dependencies` section

## Best Practices

1. **Always test locally first** - Run tests before publishing
2. **Use TestPyPI** - Test the upload process on TestPyPI first
3. **Semantic versioning** - Follow semver (MAJOR.MINOR.PATCH)
4. **Update CHANGELOG** - Document all changes before release
5. **Tag releases** - Always create git tags for releases
6. **Verify installation** - Test `pip install` after publishing
