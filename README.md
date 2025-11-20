# Meow-Meow-3000 — WAF + IDS pédagogique (DVWA)

Un mini-projet « pro »: reverse proxy WAF/IPS + moteur de signatures & scoring + logs JSON + mini dashboard.

Conçu pour:
- Développer sous Windows (avec `uv`),
- Déployer/démontrer facilement sur Kali Linux (DVWA sous Apache),
- Obtenir des résultats visuels et mesurables (403, logs, dashboard, sqlmap qui échoue).

---

## 0) Déploiement en une commande (Kali)

Option 1 — Depuis GitHub (après push du repo):

```bash
curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/deploy_kali.sh | sudo bash
```

Personnaliser (exemples):

```bash
curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/deploy_kali.sh | \
  sudo bash -s -- \
  --backend http://127.0.0.1/dvwa \
  --mode IPS \
  --waf-port 8080 \
  --dash-port 5001
```

Option 2 — Si le push GitHub n'est pas encore fait:

```bash
# Copier localement le script puis l'exécuter
scp deploy_kali.sh kali:/tmp/
ssh kali 'sudo bash /tmp/deploy_kali.sh --backend http://127.0.0.1/dvwa --mode IPS'
```

Vérification après déploiement:

```bash
# Sur la VM Kali
systemctl status meow-waf --no-pager
systemctl status meow-waf-dashboard --no-pager
curl -s http://127.0.0.1:8080/healthz
# Accès navigateur: http://<ip_kali>:8080/  et  http://<ip_kali>:5001/dashboard
```

---

### Push sur GitHub (si nécessaire)

Si tu veux que le déploiement via `curl` fonctionne directement depuis GitHub, pousse ce repo vers
`https://github.com/Aionmizu/meow-meow-3000`.

Option A — Script PowerShell (Windows):

```powershell
# Depuis la racine du projet
# Utiliser SSH ou un token PAT dans l'URL
# SSH:
.\scripts\push_to_github.ps1 -RemoteUrl "git@github.com:Aionmizu/meow-meow-3000.git" -Branch main
# HTTPS avec token:
.\scripts\push_to_github.ps1 -RemoteUrl "https://<TOKEN>@github.com/Aionmizu/meow-meow-3000.git" -Branch main
```

Option B — Commandes git manuelles:

```powershell
git init
git add -A
git commit -m "chore: deployment script + docs"
git branch -M main
git remote add origin git@github.com:Aionmizu/meow-meow-3000.git
# ou: https://<TOKEN>@github.com/Aionmizu/meow-meow-3000.git
git push -u origin main
```

Après le push, la commande d’installation one-liner fonctionne:

```bash
curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/deploy_kali.sh | sudo bash
```

---

## 1) Stack & Ports
- Backend DVWA (Kali): `http://127.0.0.1/dvwa` par défaut (remplace par IP Kali si besoin)
- WAF/Proxy: écoute `0.0.0.0:8080`
- Dashboard: écoute `0.0.0.0:5001`

En prod/démo: tu accèdes à DVWA via `http://<host_WAF>:8080/` au lieu d'aller directement sur Apache/DVWA.

---

## 2) Installation avec uv
Pré-requis: Python ≥ 3.11 & `uv` installé.

- Installation de uv (Windows/Kali):
  - Voir https://docs.astral.sh/uv/getting-started/ (choco, scoop, pipx ou script officiel)

- Depuis la racine du projet:
  ```bash
  uv sync
  ```
  Cela installe les dépendances du `pyproject.toml`.

- Lancer le WAF/Proxy (méthode par module, fonctionne sans scripts installés):
  ```bash
  uv run -m waf.run_waf
  ```

- Lancer le Dashboard (par module):
  ```bash
  uv run -m waf.run_dashboard
  ```

- Alternatif (scripts console, après installation du projet):
  - Installe le projet en éditable (au choix):
    ```bash
    uv sync            # puis
    pip install -e .   # ou: uv pip install -e .
    ```
  - Ensuite tu peux utiliser:
    ```bash
    uv run waf-proxy
    uv run waf-dashboard
    ```
    Ou directement les exécutables créés dans l'environnement virtuel Windows:
    ```powershell
    .\.venv\Scripts\waf-proxy.exe
    .\.venv\Scripts\waf-dashboard.exe
    ```

Si tu préfères un seul terminal: lance d'abord `uv run waf-proxy`, puis dans un autre `uv run waf-dashboard`.

---

## 3) Configuration (env vars)
Tu peux contrôler le comportement via des variables d’environnement:

- `WAF_BACKEND` (str): URL de base DVWA. Par défaut `http://127.0.0.1/dvwa`.
  - Exemple pour accéder à un Kali distant: `http://192.168.56.101/dvwa`
- `WAF_MODE` (str): `IDS` (log-only) ou `IPS` (bloque > seuil). Par défaut `IPS`.
- `WAF_THRESHOLD_IDS` (int): seuil d’alerte (par défaut 5).
- `WAF_THRESHOLD_BLOCK` (int): seuil de blocage IPS (par défaut 9).
- `WAF_LISTEN_HOST`, `WAF_LISTEN_PORT`: écoute du proxy (par défaut `0.0.0.0:8080`).
- `WAF_DASHBOARD_HOST`, `WAF_DASHBOARD_PORT`: écoute du dashboard (par défaut `0.0.0.0:5001`).
- `WAF_DATA_DIR`, `WAF_LOGS_FILE`: chemins `data/` et `data/logs.json` par défaut.
- `WAF_ALLOW_QUERY_MODE_SWITCH` (0/1): autorise le param `?waf_mode=IDS|IPS` (par défaut 1).

Exemples Windows PowerShell:
```powershell
$env:WAF_BACKEND = "http://192.168.56.101/dvwa"
$env:WAF_MODE = "IPS"
uv run waf-proxy
```

Exemples Kali/bash:
```bash
export WAF_BACKEND=http://127.0.0.1/dvwa
export WAF_MODE=IPS
uv run waf-proxy
```

---

## 4) Utilisation rapide
- Ouvre DVWA via le WAF: `http://127.0.0.1:8080/`
- Bascule temporairement le mode via l’URL (si activé): `?waf_mode=IDS` ou `?waf_mode=IPS`
  - Exemple: `http://127.0.0.1:8080/vulnerabilities/sqli/?id=1&waf_mode=IDS`

- Dashboard: `http://127.0.0.1:5001/dashboard`
  - Filtres par sévérité (low/high/critical), action (ALLOW/BLOCK/ERROR), règle (contient un nom de règle)

---

## 5) Ce que fait le WAF
- Reverse proxy HTTP (GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS) → DVWA
- Normalisation avant détection: URL decode (détecte double-encodage), lowercase, retrait de `/**/`, collapse des espaces, nettoyage `%0A/%0D/%09`.
- Règles (signatures) SQLi/XSS + règles d’encodage:
  - SQLi: `' or 1=1`, `union select`, `sleep(`, `; drop table`, `%27 or 1%3d1`
  - XSS: `<script`, `onerror=`, `javascript:`, `"> <script`, `%3cscript%3e`
  - Encodage lourd: séquences `%xx` répétées
- Scoring:
  - Somme des scores des règles matchées
  - +3 si encodage présent, +4 si double-encodage détecté
  - Sévérité: <5 low, 5–8 high, ≥9 critical
- Modes:
  - IDS: log seulement
  - IPS: block en 403 si `score >= WAF_THRESHOLD_BLOCK` (par défaut 9)

Chaque requête produit une ligne JSON dans `data/logs.json`:
```json
{
  "timestamp": "...",
  "request_id": "...",
  "source_ip": "...",
  "method": "GET",
  "url": "http://waf:8080/...",
  "backend_url": "http://127.0.0.1/dvwa/...",
  "score": 12,
  "severity": "critical",
  "matched_rules": ["SQLI_UNION_SELECT", "ENC_PERCENT_HEAVY"],
  "flags": {"had_encoding": true, "double_decoded": false},
  "action": "BLOCK",
  "status": 403,
  "user_agent": "...",
  "response_time_ms": 3
}
```

---

## 6) Attaques de test (manuel)
- SQLi simple:
  ```bash
  curl "http://127.0.0.1:8080/vulnerabilities/sqli/?id=1' or 1=1-- -&Submit=Submit"
  ```
- XSS simple:
  ```bash
  curl "http://127.0.0.1:8080/?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E"
  ```
- Double encodage:
  ```bash
  curl "http://127.0.0.1:8080/?q=%2527%2520or%25201%253d1"
  ```

Vérifie dans `data/logs.json` et dans le dashboard les scores et actions.

---

## 7) Attaques automatisées (pour le rapport)
- sqlmap via proxy WAF (en IPS):
  ```bash
  sqlmap -u "http://127.0.0.1:8080/vulnerabilities/sqli/?id=1&Submit=Submit" --level=5 --risk=3 --batch
  ```
  Attendu: beaucoup de requêtes bloquées (403), logs avec scores élevés.

- nikto (attaque web générique) en visant le WAF: `http://127.0.0.1:8080/`
- OWASP ZAP: scanner la cible via le WAF.

Fais des captures d’écran (403, dashboard, extraits de logs) pour le PDF.

---

## 8) Structure du code
- `waf/config.py` — settings (env vars)
- `waf/rules.py` — normalisation + signatures regex
- `waf/scoring.py` — scoring et sévérité
- `waf/logger.py` — appends JSONL dans `data/logs.json`
- `waf/proxy.py` — reverse proxy + décision IDS/IPS + log
- `waf/dashboard_app.py` — mini serveur Flask + API `/api/logs`
- `waf/templates/dashboard.html` — UI
- `waf/static/style.css` — styles

Entrypoints:
- `waf-proxy` → `waf.run_waf:main`
- `waf-dashboard` → `waf.run_dashboard:main`

---

## 9) Notes DVWA (Kali)
- Si DVWA écoute sur `http://127.0.0.1/dvwa` côté Kali et que le WAF tourne sur Kali, laisse `WAF_BACKEND` par défaut.
- Si tu développes sous Windows et que DVWA est sur une VM Kali, remplace `WAF_BACKEND` par l’IP de Kali (ex: `http://192.168.56.101/dvwa`).
- Le WAF renvoie les en-têtes: `X-WAF-Score`, `X-WAF-Severity`, `X-WAF-Action`, `X-Request-ID`.

---

## 10) Suivi interne (.junie)
- Consulte `.junie/README.md` et mets à jour `.junie/ACTION_LOG.md` à chaque étape (voir modèle ci-dessous).

Modèle d’entrée dans `.junie/ACTION_LOG.md`:
```md
## 2025-11-20 15:24
- Action: Implémentation du proxy + scoring de base
- Raison: Préparer la démo IPS/IDS
- Impact: Ajout des modules, scripts, logs JSONL, dashboard
- Suivi: Tester contre DVWA, valider blocage sqlmap
```

---

## 11) Limitations & idées d’amélioration
- Couverture de signatures limitée (mais facile à étendre)
- Pas de parsing multipart/form-data avancé pour l’instant
- Pas de corrélation multi-requêtes par IP/session
- Pas d’apprentissage automatique (juste signatures + scoring)

Idées: ajouter whitelists par chemin, rate limiting simple, intégration Grafana/Promtail, stockage SQLite pour le dashboard.


---

### 12) Troubleshooting — Hatchling build error with uv
If you see an error like:

```
Unable to determine which files to ship inside the wheel ...
The most likely cause is that there is no directory that matches the name of your project
```

This happens because the project name (`meow-meow-3000`) does not match the package directory (`waf`).

Fix (already applied in this repo): `pyproject.toml` contains:

```toml
[tool.hatch.build.targets.wheel]
packages = ["waf"]
include = ["waf/templates/**", "waf/static/**"]

[tool.hatch.build.targets.sdist]
include = ["waf/**", "README.md", "pyproject.toml"]
```

After pulling these changes, run:

```powershell
uv sync
uv run waf-proxy
uv run waf-dashboard
```

If the error persists, bypass console scripts and run by module (does not rely on build):

```powershell
uv run -m waf.run_waf
uv run -m waf.run_dashboard
```
