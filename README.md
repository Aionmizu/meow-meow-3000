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
 
# Vérification complète en une commande
bash scripts/verify_kali.sh
```

---

### Push sur GitHub (si nécessaire)

Si tu veux que le déploiement via `curl` fonctionne directement depuis GitHub, pousse ce repo vers
`https://github.com/Aionmizu/meow-meow-3000`.

Important: n’exécute pas un script PowerShell (.ps1) avec Bash. Sur Linux/Kali utilise le script Bash fourni; sous Windows utilise le script PowerShell.

Option A — Linux/Kali/macOS (Bash):

```bash
bash scripts/push_to_github.sh --remote https://github.com/Aionmizu/meow-meow-3000.git --branch main
# SSH (si clé configurée)
bash scripts/push_to_github.sh --remote git@github.com:Aionmizu/meow-meow-3000.git --branch main
```

Option B — Windows PowerShell (HTTPS avec prompts interactifs / Git Credential Manager):

```powershell
# Depuis la racine du projet
.\scripts\push_to_github.ps1 -RemoteUrl "https://github.com/Aionmizu/meow-meow-3000.git" -Branch main -UseCredentialManager
```

Option C — Windows PowerShell via SSH (optionnel):

```powershell
.\scripts\push_to_github.ps1 -RemoteUrl "git@github.com:Aionmizu/meow-meow-3000.git" -Branch main
```

Option D — HTTPS avec PAT dans l’URL (moins recommandé, évite de coller les tokens en clair):

```powershell
.\scripts\push_to_github.ps1 -RemoteUrl "https://<TOKEN>@github.com/Aionmizu/meow-meow-3000.git" -Branch main
```

Option E — Commandes git manuelles (HTTPS avec prompts):

```powershell
git init
git add -A
git commit -m "chore: deployment script + docs"
git branch -M main
git remote add origin https://github.com/Aionmizu/meow-meow-3000.git
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


---

## Annexes — Résoudre « Permission denied (publickey) » lors du push Git

Ne pas utiliser sudo/Administrateur avec Git. Si vous voyez cette erreur, suivez ces étapes (Windows PowerShell):

1) Vérifier la connectivité SSH à GitHub
- Commande:
```
ssh -vT git@github.com
```
- Attendu: un message « Hi USERNAME! You've successfully authenticated… » ou similaire. Si vous voyez « Permission denied (publickey) », continuez.

2) Générer et charger une clé SSH (recommandé type ed25519)
- Utilisez le script fourni:
```
# Depuis la racine du projet
.\scripts\setup_github_ssh.ps1 -Email "marjolinf@gmail.com"
```
- Le script:
  - démarre le service ssh-agent,
  - génère une clé à %USERPROFILE%\.ssh\id_ed25519 (si absente),
  - charge la clé dans l’agent,
  - affiche votre clé publique.
- Copiez la ligne affichée et ajoutez-la dans GitHub: https://github.com/settings/ssh/new
- Puis testez à nouveau:
```
ssh -T git@github.com
```

3) Configurer le remote et pousser
- SSH:
```
.\scripts\push_to_github.ps1 -RemoteUrl "git@github.com:Aionmizu/meow-meow-3000.git" -Branch main -Force
```
- HTTPS (si vous préférez un Personal Access Token/PAT):
```
# Générez un PAT (classic) avec scope repo et collez-le à la place de <TOKEN>
.\scripts\push_to_github.ps1 -RemoteUrl "https://<TOKEN>@github.com/Aionmizu/meow-meow-3000.git" -Branch main -Force
```

Notes:
- Si vous utilisez une invite différente (Git Bash), lancez l’agent:
```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```
- Si vous avez déjà un remote origin, ajoutez -Force pour le remplacer.
- Si `ssh -T` continue d’échouer, vérifiez que la clé publique ajoutée est exactement celle affichée par le script et que vous n’êtes pas derrière un proxy qui bloque le port 22. En dernier recours, utilisez SSH over HTTPS: https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port


---

## 13) Fonctionnalités détaillées (WAF + IDS + IPS + Dashboard)

Voici la liste exhaustive des fonctionnalités actuellement implémentées, telles qu’elles existent dans le code de ce dépôt.

- Reverse proxy HTTP complet
  - Méthodes supportées: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS.
  - Reconstruction propre de l’URL cible: jointure du chemin backend (`WAF_BACKEND`) et du chemin demandé côté client.
  - Transmission du corps de requête en binaire (bytes) sans altération.
  - Hygiène des en‑têtes côté requête: suppression des hop‑by‑hop (`Connection`, `Keep-Alive`, `Transfer-Encoding`, `Upgrade`, etc.), réécriture du `Host` pour correspondre au backend.
  - Ajout des en‑têtes de provenance: `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`.
  - Filtrage des en‑têtes côté réponse: suppression de `Content-Encoding`, `Transfer-Encoding`, `Connection` afin d’éviter les incohérences.

- Modes de fonctionnement
  - IDS: n’applique aucun blocage, mais journalise et annote la réponse (en‑têtes `X‑WAF‑*`).
  - IPS: bloque en 403 si le score atteint le seuil de blocage; sinon, proxifie normalement.
  - Bascule temporaire (démo): si `WAF_ALLOW_QUERY_MODE_SWITCH=1`, le paramètre `?waf_mode=IDS|IPS` peut surcharger le mode courant pour une requête donnée.

- Moteur de normalisation et détection
  - Zone analysée: concaténation de `path + query + body + User-Agent + Referer + Cookie`.
  - Normalisation: 1× URL decode + détection de double-décodage, passage en minuscules, retrait des commentaires `/**/`, nettoyage de `%0A/%0D/%09`, réduction des espaces.
  - Signatures (regex) pour SQLi, XSS et encodage suspect (liste détaillée dans la section 14).

- Scoring, sévérité, décisions
  - Score = somme des points des signatures détectées + bonus d’encodage (+3 si présence de `%`) + bonus double-décodage (+4 si une seconde passe de decode change le texte).
  - Sévérité: `<5 = low`, `5–8 = high`, `>=9 = critical`.
  - Décision: en IPS, `BLOCK` si `score >= WAF_THRESHOLD_BLOCK` (9 par défaut); sinon `ALLOW`. En IDS, toujours `ALLOW`.

- Santé et visibilité
  - Endpoint `GET /healthz` renvoyant un JSON minimal `{"status":"ok","mode":"IDS|IPS"}`.
  - Ajout d’en‑têtes sur toutes les réponses: `X-WAF-Score`, `X-WAF-Severity`, `X-WAF-Action`, `X-Request-ID`.

- Journalisation (JSON Lines)
  - Fichier: `data/logs.json` (chemin configurable).
  - Un enregistrement par requête: `timestamp`, `request_id`, `source_ip`, `method`, `url`, `backend_url`, `score`, `severity`, `matched_rules`, `flags` (`had_encoding`, `double_decoded`), `action`, `status`, `user_agent`, `response_time_ms`.
  - Résilience: création automatique du dossier `data/` si absent; utilisation de `orjson` si disponible (sinon JSON standard).

- Dashboard (supervision)
  - UI Flask: `/dashboard` (également `/`).
  - API: `GET /api/logs` avec filtres `severity`, `action`, `rule` et `limit`; pagination simple (coupe en fin de liste).
  - Front minimaliste: tableau des événements, couleurs par sévérité et action, auto‑refresh (~2 s).

- Déploiement Kali automatisé
  - Script `deploy_kali.sh` installant les prérequis, clonant/màj le repo, créant une venv, installant le projet, déposant des services systemd (`meow-waf`, `meow-waf-dashboard`), ouvrant les ports UFW si nécessaire et effectuant un smoke test.
  - Fichier d’environnement `/etc/default/meow-waf` pour centraliser la configuration (ports, backend, mode, chemins).

- Configuration par variables d’environnement
  - `WAF_BACKEND`, `WAF_MODE`, `WAF_THRESHOLD_IDS`, `WAF_THRESHOLD_BLOCK`.
  - `WAF_LISTEN_HOST`, `WAF_LISTEN_PORT`, `WAF_DASHBOARD_HOST`, `WAF_DASHBOARD_PORT`.
  - `WAF_DATA_DIR`, `WAF_LOGS_FILE`, `WAF_ALLOW_QUERY_MODE_SWITCH`.

- Compatibilité d’exécution
  - Développement: `uv run -m waf.run_waf` et `uv run -m waf.run_dashboard` (indépendant des scripts console).
  - Scripts console disponibles après installation (`waf-proxy`, `waf-dashboard`).

---

## 14) Règles de gestion détaillées (détection, scoring, blocage, logs)

Cette section détaille précisément les règles et la logique appliquées par le WAF/IPS, telles qu’implémentées dans `waf/rules.py`, `waf/scoring.py`, `waf/proxy.py`.

1) Normalisation (entrée du moteur)
- Entrée analysée = concaténation des segments: `path + query + body + User-Agent + Referer + Cookie`.
- Étapes appliquées:
  - Décodage URL 1× (unquote_plus) puis tentative d’un second décodage pour détecter un double encodage (sans conserver la chaîne double‑décodée si cela ne change rien).
  - Mise en minuscules de l’ensemble du texte.
  - Retrait des commentaires de contournement `/**/` (remplacés par un espace).
  - Remplacement des séquences `%0A` (LF), `%0D` (CR), `%09` (Tab) résiduelles par des espaces si présentes.
  - Réduction des espaces blancs consécutifs en un seul espace; trim en début/fin.
- Indicateurs retournés (flags):
  - `had_encoding`: booléen, vrai si au moins un caractère `%` est présent dans la chaîne d’origine.
  - `double_decoded`: booléen, vrai si une seconde passe de décodage modifie effectivement la chaîne.

2) Signatures (regex) et points associés
- SQLi
  - `SQLI_OR_1EQ1` — 5 pts — `(['"]\s*or\s*1\s*=\s*1)`
    - Détecte l’expression `or 1=1` précédée d’une quote simple ou double.
  - `SQLI_UNION_SELECT` — 5 pts — `\bunion\s+select\b`
    - Détecte l’usage de `UNION SELECT`.
  - `SQLI_SLEEP_FN` — 4 pts — `\bsleep\s*\(`
    - Détecte la fonction de temporisation `sleep(`.
  - `SQLI_DROP_TABLE` — 6 pts — `;\s*drop\s+table`
    - Détecte l’enchaînement d’instructions avec suppression de table.
  - `SQLI_HEX_ENC_OR` — 4 pts — `%27\s*or\s*1%3d1`
    - Détecte la variante encodée URL de `' or 1=1` (`%27` pour `'`, `%3d` pour `=`).

- XSS
  - `XSS_SCRIPT_TAG` — 5 pts — `<\s*script\b`
    - Détecte la balise `<script>`.
  - `XSS_ATTR_ONERROR` — 4 pts — `onerror\s*=`
    - Détecte un attribut d’événement dangereux.
  - `XSS_JS_PROTO` — 4 pts — `javascript:\s*`
    - Détecte l’URI scheme `javascript:`.
  - `XSS_QUOTE_BREAK_SCRIPT` — 5 pts — `"\s*>\s*<\s*script`
    - Détecte une cassure de guillemet suivie d’un `<script>`.
  - `XSS_ENC_SCRIPT` — 4 pts — `%3c\s*script\s*%3e`
    - Détecte `<script>` encodé (`%3Cscript%3E`).

- Encodage suspect
  - `ENC_PERCENT_HEAVY` — 3 pts — `%[0-9a-f]{2}(%[0-9a-f]{2}){2,}`
    - Détecte des séquences `%xx` répétées (encodage lourd typique d’évasion).

3) Scoring et sévérité
- Score total = somme des points de toutes les signatures détectées sur le texte normalisé.
- Bonus:
  - `+3` si `had_encoding == true` (présence de `%` dans la chaîne d’origine).
  - `+4` si `double_decoded == true` (la seconde passe de decode modifie la chaîne).
- Sévérité (affichée dans les en‑têtes et le dashboard):
  - `< 5` → `low`
  - `5–8` → `high`
  - `>= 9` → `critical`

4) Logique de décision (IPS/IDS)
- Mode IDS: n’applique aucun blocage; l’action est toujours `ALLOW` (les en‑têtes et les logs sont renseignés).
- Mode IPS: 
  - `BLOCK` (HTTP 403) si `score >= WAF_THRESHOLD_BLOCK` (valeur par défaut: 9).
  - `ALLOW` sinon (la requête est transmise au backend et la réponse du backend est renvoyée telle quelle, avec les en‑têtes `X‑WAF‑*`).
- Erreurs de communication avec le backend (timeouts, etc.): `ERROR` (HTTP 502) et log d’erreur détaillé.

5) En‑têtes ajoutés sur toutes les réponses
- `X-WAF-Score: <int>`
- `X-WAF-Severity: low|high|critical|none`
- `X-WAF-Action: ALLOW|BLOCK|ERROR`
- `X-Request-ID: <uuid4-hex>`

6) Journalisation (une ligne par requête)
- Champs enregistrés:
  - `timestamp` (UTC ISO8601), `request_id`, `source_ip`, `method`, `url` (côté WAF), `backend_url`, `score`, `severity`, `matched_rules` (liste des noms), `flags` (objet), `action`, `status` (HTTP), `user_agent`, `response_time_ms`.
- Format: JSON Lines (une ligne = un objet JSON), fichier par défaut `data/logs.json`.
- Le Dashboard lit ce fichier en lecture seule et expose l’API `/api/logs`.

7) Configuration et seuils (rappel)
- `WAF_MODE`: `IDS` ou `IPS` (défaut `IPS`).
- `WAF_THRESHOLD_BLOCK`: entier, seuil de blocage en mode IPS (défaut 9).
- `WAF_THRESHOLD_IDS`: entier, seuil d’alerte conceptuel (la sévérité `high` commence à 5).
- `WAF_BACKEND`: URL base de DVWA (attention à la casse `dvwa` vs `DVWA`).
- Hôtes/ports: `WAF_LISTEN_HOST/PORT` (proxy), `WAF_DASHBOARD_HOST/PORT` (dashboard).
- Données: `WAF_DATA_DIR`, `WAF_LOGS_FILE`.
- Démo: `WAF_ALLOW_QUERY_MODE_SWITCH=1` pour autoriser `?waf_mode=...`.

8) Exemples pratiques de décisions
- `id=1' or 1=1` → Score 5 → `high` → ALLOW (par défaut, sauf si `WAF_THRESHOLD_BLOCK <= 5`).
- `id=1' union select 1,2-- -` → Score 5 → `high` → ALLOW (par défaut).
- `id=%27%20or%201%3d1%20union%20select%201,2` → `SQLI_HEX_ENC_OR` (4) + `UNION` (5) + encodage (+3) = 12 → `critical` → BLOCK (IPS).
- Double encodage (`%2527...`) ajoute +4 au total, ce qui pousse rapidement au‑delà de 9.

9) Limites et considérations
- La signature `OR 1=1` sans guillemet (ex: `1 or 1=1`) n’est pas détectée par défaut pour limiter les faux positifs. Elle peut être ajoutée si besoin.
- `UNION SELECT` seul ne suffit pas à bloquer par défaut (5 pts). Les charges utiles encodées et/ou combinées dépassent le seuil.
- Pas de persistance de bannissement IP native (décision par requête). Un bannissement basique ou un rate‑limiting peuvent être ajoutés facilement si nécessaire.

Si tu souhaites modifier l’agressivité (seuils ou signatures), vois la section 11 “Limitations & idées d’amélioration” et n’hésite pas à ouvrir un ticket en listant les cas souhaités.


---

## 15) Mettre à jour une installation existante sur Kali

Si tu as déjà déployé le projet avec `deploy_kali.sh` dans `/opt/meow-meow-3000`, tu peux mettre à jour le code (nouvelles règles, correctifs) en une commande:

Option 1 — depuis GitHub (après push du repo):

```bash
autossh_opts="" # laisser vide en général
curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/scripts/update_kali.sh | sudo bash
```

Option 2 — depuis le checkout local sur la VM:

```bash
sudo bash scripts/update_kali.sh
```

Options utiles:
- `--install-dir /opt/meow-meow-3000` (par défaut)
- `--branch main` (par défaut)
- `--repo https://github.com/Aionmizu/meow-meow-3000.git` (par défaut)
- `--no-restart` (ne redémarre pas les services; utile pour tester à chaud)

Le script:
- récupère les dernières sources (git fetch/reset),
- réinstalle le paquet dans la venv (`pip install -e .`),
- recharge/redémarre les services `meow-waf` et `meow-waf-dashboard`,
- vérifie `/healthz` et affiche un récapitulatif.

Nouvelle couverture de signatures (renforcée):
- SQLi: `SQLI_BARE_OR_1EQ1` (4 pts), `SQLI_UNION_SELECT` passe à 6 pts, `SQLI_COMMENT_DASH` (2), `SQLI_STACKED_QUERIES` (4)
- Fichiers/OS: `PATH_TRAVERSAL` (3), `LFI_WRAPPER` (4), `CMD_INJECTION` (4)
- XSS: `XSS_IMG_ONERROR` (4)

Conséquence: des charges utiles `UNION SELECT` encodées passent plus facilement au‑dessus du seuil (bonus encodage +3), et certaines tentatives de double encodage combinées déclenchent des `BLOCK` (≥ 9) plus souvent.
