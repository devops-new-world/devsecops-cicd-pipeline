# 🚀 Book Ticketing App — DevSecOps CI/CD Pipeline

A production-grade **DevSecOps pipeline** for the Book Ticketing App built on GitHub Actions. Every code push is automatically linted, security-scanned, containerized, and quality-gated before it can reach production.

---

## 📋 Table of Contents

- [What is DevSecOps?](#what-is-devsecops)
- [Pipeline Overview](#pipeline-overview)
- [Pipeline Flow Diagram](#pipeline-flow-diagram)
- [Job Details](#job-details)
  - [1. Lint & Format](#1--lint--format)
  - [2. SAST Scan](#2--sast-scan)
  - [3. Dependency Scan](#3--dependency-scan)
  - [4. Build & Push Image](#4--build--push-image)
  - [5. Container Scan](#5--container-scan)
  - [6. SonarCloud Quality Gate](#6--sonarcloud-quality-gate)
- [Secrets & Configuration](#secrets--configuration)
- [Security Tools Explained](#security-tools-explained)
- [SARIF & GitHub Security Tab](#sarif--github-security-tab)
- [Dockerfile Security](#dockerfile-security)
- [Known Issues & Fixes Applied](#known-issues--fixes-applied)
- [Local Development](#local-development)

---

## What is DevSecOps?

**DevSecOps** = **Dev**elopment + **Sec**urity + **Op**erations

Traditionally, security was checked at the end of development — often too late and too expensive to fix. DevSecOps **shifts security left**, meaning security checks run automatically on every single commit, alongside regular CI/CD steps.

```
Traditional:  Code → Build → Test → Deploy → 🔒 Security (too late!)
DevSecOps:    Code → 🔒 Lint → 🔒 SAST → 🔒 SCA → Build → 🔒 Container Scan → Deploy
```

Benefits:
- Vulnerabilities caught in seconds, not weeks
- No manual security review bottleneck
- Audit trail of every scan result
- Developers get immediate feedback

---

## Pipeline Overview

The pipeline triggers on:
- Every **push** to `main` or `develop`
- Every **pull request** targeting `main`

It runs **6 jobs** in a dependency chain — later jobs only run if earlier ones pass:

| Job | Tool(s) | Purpose |
|-----|---------|---------|
| 🔍 Lint & Format | Black, isort, Flake8 | Code style enforcement |
| 🔒 SAST Scan | Bandit, Semgrep | Static security analysis |
| 📦 Dependency Scan | Snyk | Known CVEs in packages |
| 🐳 Build & Push | Docker, GHCR | Build & publish container image |
| 🛡️ Container Scan | Trivy | Vulnerabilities inside the image |
| 📊 Quality Gate | SonarCloud | Code quality & coverage |

---

## Pipeline Flow Diagram

```
Push / Pull Request
        │
        ▼
┌───────────────┐
│  🔍 lint      │  ← Always runs first
└───────┬───────┘
        │
   ┌────┴────────────────────┐
   ▼                         ▼
┌──────────┐          ┌──────────────────┐
│ 🔒 sast  │          │ 📦 dependency-   │
│          │          │    scan          │
└────┬─────┘          └────────┬─────────┘
     │                         │
     └──────────┬──────────────┘
                ▼
        ┌───────────────┐
        │  🐳 build     │  ← Only if SAST + Dep scan pass
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │ 🛡️ container- │  ← Scans the built image
        │    scan       │
        └───────────────┘

┌────────────────────────┐
│ 📊 sonarcloud          │  ← Runs in parallel with sast/dep-scan
└────────────────────────┘
```

---

## Job Details

### 1. 🔍 Lint & Format

**What it does:** Enforces consistent Python code style and auto-fixes formatting issues before any security or quality checks run.

**Tools used:**

| Tool | Version | Role |
|------|---------|------|
| [Black](https://black.readthedocs.io) | 24.4.2 | Auto-formatter — opinionated, zero-config |
| [isort](https://pycqa.github.io/isort/) | 5.13.2 | Sorts and organizes import statements |
| [Flake8](https://flake8.pycqa.org) | 7.0.0 | Linter — catches syntax errors and style violations |

**How it works step by step:**

1. Checks out the code with write permissions (needed to commit fixes)
2. Installs Black, isort, and Flake8
3. Runs `black src/` — auto-formats all Python files in `src/`
4. Runs `isort --profile black src/` — sorts imports to be compatible with Black
5. **Auto-commits** any formatting changes back to the branch using `git-auto-commit-action`
6. Re-runs Black and isort in `--check` mode to verify everything is clean
7. Runs Flake8 to catch any remaining style issues

**Why auto-commit?** Developers shouldn't have to manually run formatters. The pipeline fixes it for them and commits with the message `style: auto-format with black and isort`.

**Fails if:** Flake8 finds style violations that Black/isort couldn't auto-fix.

---

### 2. 🔒 SAST Scan

**SAST = Static Application Security Testing** — analyzes source code without running it.

**Runs after:** `lint` ✅

**Tools used:**

| Tool | Role |
|------|------|
| [Bandit](https://bandit.readthedocs.io) | Python-specific security linter |
| [Semgrep](https://semgrep.dev) | Multi-language pattern-based SAST with OWASP rules |

**Bandit — what it finds:**
- Hardcoded passwords and secrets
- Use of insecure functions (`eval`, `exec`, `subprocess` with `shell=True`)
- Weak cryptography (MD5, SHA1)
- SQL injection patterns
- Insecure file permissions

Bandit results are saved as `bandit-report.json` and uploaded as a GitHub Actions artifact for download.

**Semgrep — what it finds:**
Runs 4 rule sets simultaneously:
- `p/owasp-top-ten` — OWASP Top 10 vulnerabilities (injection, XSS, broken auth, etc.)
- `p/python` — Python-specific security patterns
- `p/secrets` — Hardcoded API keys, tokens, passwords
- `p/jwt` — JWT implementation vulnerabilities

Results are saved as `semgrep.sarif` and uploaded to the **GitHub Security tab**.

> **Important:** `venv/`, `.venv/`, `node_modules/`, and `tests/` are excluded from Semgrep scanning. Without exclusions, Semgrep scans pip's own internal vendored code and generates 26+ false positive findings.

**Fails if:** Semgrep finds blocking-severity issues in your source code (not in excluded dirs).

---

### 3. 📦 Dependency Scan

**SCA = Software Composition Analysis** — checks your third-party packages for known vulnerabilities.

**Runs after:** `lint` ✅

**Tool used:** [Snyk](https://snyk.io)

**How it works:**

1. Sanitizes `requirements.txt` — strips invalid version suffixes (e.g. `httpx==0.27.0e` → `httpx==0.27.0`) using a Python regex step
2. Installs all dependencies
3. Runs Snyk against `requirements.txt` using pip as the package manager
4. Generates `snyk.sarif` and uploads it to the **GitHub Security tab**

**What Snyk checks:**
- Every package in `requirements.txt` against the Snyk vulnerability database
- Transitive dependencies (packages your packages depend on)
- Only reports `HIGH` and `CRITICAL` severity findings (`--severity-threshold=high`)

**Requires secret:** `SNYK_TOKEN` — get one free at https://app.snyk.io

**Note:** `continue-on-error: true` is set so dependency findings don't block the build — they're reported as warnings. Change to `false` if you want to enforce a hard block.

---

### 4. 🐳 Build & Push Image

**Runs after:** `sast` ✅ AND `dependency-scan` ✅

**What it does:** Builds the Docker image from the `Dockerfile` and pushes it to **GitHub Container Registry (GHCR)**.

**Image tag format:**
```
ghcr.io/<owner>/<repo>/book-ticketing-app:<git-sha>
```

Using the full Git SHA as the tag means every image is uniquely and immutably identified. You can always trace any running container back to the exact commit it was built from.

**Authentication:** Uses `GITHUB_TOKEN` (automatically available in all GitHub Actions) — no extra secrets needed for GHCR.

**The Dockerfile (multi-stage build):**

```
Stage 1 (builder):   python:3.11-slim
                     └── pip install --user -r requirements.txt

Stage 2 (runtime):   python:3.11-slim  ← fresh, clean base
                     ├── Install curl (for healthcheck)
                     ├── Create non-root user appuser
                     ├── Copy only built packages from stage 1
                     ├── Remove SUID/SGID bits
                     └── Run as appuser on port 8080
```

Multi-stage builds keep the final image small and clean — build tools and pip cache never make it into the runtime image.

---

### 5. 🛡️ Container Scan

**Runs after:** `build` ✅

**Tool used:** [Trivy](https://trivy.dev) by Aqua Security

**What it does:** Scans the built Docker image for vulnerabilities in:
- OS packages (Debian/Ubuntu packages inside the image)
- Python packages installed in the image
- Misconfigurations in the image layers

**Severity filter:** Only `CRITICAL` and `HIGH` vulnerabilities are reported.

**How it works:**

1. Logs into GHCR to pull the private image built in the previous job
2. Runs Trivy against the image reference using the Git SHA tag
3. Outputs results as `trivy-results.sarif`
4. Uploads SARIF to the **GitHub Security tab**

> **Note:** `exit-code: '0'` is set so Trivy reports findings without blocking the pipeline. Change to `'1'` if you want to enforce a hard block on critical vulnerabilities.

> **Trivy Security Incident (2026-03-01):** Trivy's GitHub releases v0.27.0–v0.69.1 were deleted after a supply chain attack. The pipeline uses `trivy-action@0.35.0` which pulls Trivy `v0.69.3` — the first safe, stable post-incident release.

---

### 6. 📊 SonarCloud Quality Gate

**Runs after:** `lint` ✅ (in parallel with SAST and dependency scan)

**Tool used:** [SonarCloud](https://sonarcloud.io) by SonarSource

**What it does:** Deep code quality analysis including:
- Code smells and maintainability issues
- Bugs and reliability issues
- Security hotspots
- Code coverage (if tests are configured)
- Duplicate code detection
- Technical debt estimation

**How it works:**

1. Checks out with `fetch-depth: 0` — full git history is required for SonarCloud to perform blame analysis and detect which code is "new" vs existing
2. Runs the SonarCloud scanner which uploads results to your SonarCloud project dashboard
3. The Quality Gate either passes or fails based on thresholds you configure in SonarCloud

**Requires secrets:**
- `SONAR_TOKEN` — from https://sonarcloud.io → My Account → Security → Generate Token
- `GITHUB_TOKEN` — automatically available

> **Critical setup step:** In SonarCloud UI go to **Project → Administration → Analysis Method** and toggle **Automatic Analysis OFF**. If both CI analysis and Automatic Analysis run simultaneously, SonarCloud exits with code 3 and the job fails.

---

## Secrets & Configuration

Add these in **GitHub → Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Where to Get It | Required By |
|-------------|----------------|-------------|
| `SNYK_TOKEN` | https://app.snyk.io → Account Settings → API Token | Dependency Scan |
| `SONAR_TOKEN` | https://sonarcloud.io → My Account → Security | SonarCloud |
| `SEMGREP_APP_TOKEN` | https://semgrep.dev → Settings → Tokens | Semgrep (optional) |

`GITHUB_TOKEN` is **automatically** provided by GitHub Actions — you do not need to create it.

---

## Security Tools Explained

### What is SAST vs DAST vs SCA?

| Type | Full Name | When | How |
|------|-----------|------|-----|
| **SAST** | Static Application Security Testing | Before running | Reads source code |
| **DAST** | Dynamic Application Security Testing | While running | Sends real HTTP requests |
| **SCA** | Software Composition Analysis | Before running | Checks dependency versions |
| **Container Scan** | — | After build | Scans image layers |

This pipeline implements **SAST**, **SCA**, and **Container Scanning**. DAST (e.g. OWASP ZAP) would require a running instance of the app and can be added as a future step.

### What is SARIF?

**SARIF** (Static Analysis Results Interchange Format) is a standard JSON format for security tool output. GitHub's Security tab natively understands SARIF — when you upload a `.sarif` file using `github/codeql-action/upload-sarif`, the findings appear under **Security → Code Scanning Alerts** in your repo with full details, file locations, and severity levels.

### What is OWASP Top 10?

The [OWASP Top 10](https://owasp.org/www-project-top-ten/) is the most widely recognized list of critical web application security risks. Semgrep's `p/owasp-top-ten` rule set checks your code for all of them, including:

1. Broken Access Control
2. Cryptographic Failures
3. Injection (SQL, command, etc.)
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Identification and Authentication Failures
8. Software and Data Integrity Failures
9. Security Logging and Monitoring Failures
10. Server-Side Request Forgery (SSRF)

---

## SARIF & GitHub Security Tab

Three jobs upload SARIF results to GitHub's Security tab:

- **Semgrep** → `semgrep.sarif`
- **Snyk** → `snyk.sarif`
- **Trivy** → `trivy-results.sarif`

To view findings: Go to your repo → **Security** → **Code scanning** → select tool from the filter dropdown.

Each finding shows:
- File path and line number
- Severity (Critical / High / Medium / Low)
- Rule ID and description
- Link to fix documentation

---

## Dockerfile Security

The `Dockerfile` follows security best practices:

| Practice | Implementation |
|----------|---------------|
| Multi-stage build | Separate `builder` and `runtime` stages — build tools never reach production |
| Non-root user | `appuser` created and used — containers don't run as root |
| Minimal base image | `python:3.11-slim` — smallest official Python image |
| SUID/SGID removal | `find / -perm /6000 -exec chmod a-s` — prevents privilege escalation |
| Healthcheck | `/health` endpoint checked every 30s |
| Package chown | All copied files owned by `appuser` |
| No cache | `--no-cache-dir` on pip — reduces image size |
| DEBIAN_FRONTEND | `noninteractive` — suppresses apt-get dialog warnings |

---

## Known Issues & Fixes Applied

All issues encountered during pipeline development and their resolutions:

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | SonarCloud exit code 3 | CI Analysis + Automatic Analysis both enabled | Disable Automatic Analysis in SonarCloud UI |
| 2 | `sonarcloud-github-action@master` deprecated | Deprecated action | Replaced with `sonarqube-scan-action@v5.0.0` |
| 3 | Semgrep 26 false positives | `venv/` directory scanned (pip internals) | Added `--exclude venv` flags |
| 4 | `semgrep-action@v2` not found | v2 does not exist — action fully deprecated | Run `semgrep scan` via pip install directly |
| 5 | `httpx==0.27.0e` breaks pip | Invalid version suffix in `requirements.txt` | Python regex sanitize step strips trailing letters |
| 6 | `snyk.sarif` path does not exist | Snyk failed silently, no SARIF produced | `hashFiles()` guard on upload step |
| 7 | Snyk Poetry validation error | Snyk tried to parse `pyproject.toml` | `--package-manager=pip` argument added |
| 8 | Trivy binary download fails | Trivy releases v0.27–v0.69.1 deleted (supply chain attack 2026-03-01) | Upgraded to `trivy-action@0.35.0` → Trivy v0.69.3 |
| 9 | `trivy-results.sarif` path does not exist | Trivy couldn't pull image (no GHCR auth) | Added `docker/login-action` before Trivy step |
| 10 | `codeql-action/upload-sarif@v3` deprecated | v3 deprecated December 2026 | Upgraded all occurrences to `@v4` |
| 11 | Dockerfile healthcheck fails | `curl` not installed in `python:3.11-slim` | `apt-get install curl` added to runtime stage |
| 12 | `appuser` can't read installed packages | `/root/.local` copied without `--chown` | `--chown=appuser:appuser` on COPY |

---

## Local Development

Run the security tools locally before pushing:

```bash
# Install all dev tools
pip install black==24.4.2 flake8==7.0.0 isort==5.13.2 bandit semgrep

# Format code
black src/
isort --profile black src/

# Lint
flake8 src/

# SAST — Bandit
bandit -r src/ -f json -o bandit-report.json

# SAST — Semgrep
semgrep scan \
  --config p/owasp-top-ten \
  --config p/python \
  --config p/secrets \
  --exclude venv \
  .

# Fix invalid versions in requirements.txt
sed -i -E 's/(==[0-9]+\.[0-9]+\.[0-9]+)[a-zA-Z][a-zA-Z0-9]*/\1/g' requirements.txt

# Build Docker image locally
docker build -t book-ticketing-app:local .

# Scan local image with Trivy
trivy image book-ticketing-app:local
```

---

## Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── ci-pipeline.yml     # Main CI/CD pipeline
├── src/                        # Application source code
├── Dockerfile                  # Multi-stage secure container build
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Black, isort, Bandit configuration
├── sonar-project.properties    # SonarCloud project config
└── README.md                   # This file
```

---

## Pipeline Status

> Add these badges to the top of your README by going to  
> **Actions → select workflow → ⋯ → Create status badge**

```markdown
![CI Pipeline](https://github.com/<owner>/<repo>/actions/workflows/ci-pipeline.yml/badge.svg)
```