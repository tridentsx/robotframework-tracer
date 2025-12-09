# PyPI Setup - Quick Reference

## One-Time Setup (5 minutes)

### 1. Create PyPI Account
→ https://pypi.org/account/register/
- Register and verify email
- Enable 2FA

### 2. Create API Token
→ https://pypi.org/manage/account/token/
- Click "Add API token"
- Name: `robotframework-tracer`
- Scope: "Entire account"
- **Save the token** (starts with `pypi-`)

### 3. Add Token to GitHub
→ https://github.com/tridentsx/robotframework-tracer/settings/secrets/actions
- Click "New repository secret"
- Name: `PYPI_TOKEN`
- Value: Paste your token
- Click "Add secret"

## That's It!

Now every time you create a GitHub release, it will automatically publish to PyPI.

## Test It (Optional)

Want to test before the real release?

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Upload to TestPyPI (test environment)
python -m twine upload --repository testpypi dist/*
# Username: __token__
# Password: <your-token>

# Test install
pip install --index-url https://test.pypi.org/simple/ robotframework-tracer
```

## Future Releases

```bash
# 1. Update version
echo 'VERSION = "0.2.0"' > src/robotframework_tracer/version.py

# 2. Update CHANGELOG.md

# 3. Commit, tag, and create release
git add . && git commit -m "Bump version to 0.2.0"
git push
git tag v0.2.0 && git push origin v0.2.0
gh release create v0.2.0 --title "v0.2.0" --notes "What's new..."

# GitHub Actions will automatically publish to PyPI!
```

## Verify Publication

After release, check:
- PyPI page: https://pypi.org/project/robotframework-tracer/
- Install: `pip install robotframework-tracer`

---

See [docs/PUBLISHING.md](docs/PUBLISHING.md) for detailed documentation.
