# Meow-Meow-3000 — WAF + IDS pédagogique (DVWA)

Mini WAF/IPS de démonstration pour DVWA: reverse proxy, règles SQLi/XSS, scoring, logs JSONL et dashboard web.

## Vue d'ensemble
- Flux: **client → WAF (port 80) → DVWA (port 8080)**.
- Le WAF réécrit les redirections et ajoute les en-têtes `X-WAF-*` pour chaque réponse.
- Dashboard live pour consulter/filtrer les logs et maintenant un bouton **Clear logs** pour purger `data/logs.json`.

## Déploiement rapide (Kali)
Exécution en une commande (DVWA déjà installé sur le même hôte, écoutant en 8080):
```bash
curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/deploy_kali.sh | sudo bash
```

Options utiles (sans `/dvwa` dans le backend pour éviter les boucles):
```bash
curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/deploy_kali.sh | \
  sudo bash -s -- \
  --backend http://127.0.0.1:8080 \
  --mode IPS \
  --waf-port 80 \
  --dash-port 5001
```

Après installation:
- Services systemd: `meow-waf` (proxy) et `meow-waf-dashboard` (dashboard).
- Santé: `curl -s http://127.0.0.1/healthz` (HTTP 200 attendu).
- UI: `http://<ip_kali>/` (WAF) et `http://<ip_kali>:5001/dashboard` (dashboard).

## Ports et config par défaut
- **WAF**: `0.0.0.0:80`
- **DVWA attendu**: `http://127.0.0.1:8080` (ne pas ajouter `/dvwa`).
- **Dashboard**: `0.0.0.0:5001`

Variables d'environnement clés (fichier `/etc/default/meow-waf` généré par le script):
- `WAF_BACKEND`: URL DVWA (ex: `http://127.0.0.1:8080`).
- `WAF_MODE`: `IDS` ou `IPS` (par défaut `IPS`).
- `WAF_THRESHOLD_IDS` / `WAF_THRESHOLD_BLOCK`: seuils (5 / 9 par défaut).
- `WAF_LISTEN_HOST` / `WAF_LISTEN_PORT`: écoute du proxy (par défaut `0.0.0.0:80`).
- `WAF_DASHBOARD_HOST` / `WAF_DASHBOARD_PORT`: écoute du dashboard (par défaut `0.0.0.0:5001`).
- `WAF_DATA_DIR`, `WAF_LOGS_FILE`: chemins vers les données/logs.

## Exécution locale (dev)
```bash
uv sync
uv run -m waf.run_waf         # proxy
uv run -m waf.run_dashboard   # dashboard
```
Pense à définir `WAF_BACKEND=http://127.0.0.1:8080` (sans `/dvwa`).

## Requêtes de test (copier/coller)
Utilise l'URL du **WAF** (port 80). Ces charges doivent apparaître dans les logs et être bloquées en IPS (seuil 9).

```bash
# SQLi classique (UNION + quote encodée)
curl -i "http://<ip_waf>/vulnerabilities/sqli/?id=%27%20or%201%3d1%20union%20select%201,2--+&Submit=Submit"

# SQLi time-based : 1 and sleep(2) --+
curl -i "http://<ip_waf>/vulnerabilities/sqli_blind/?id=1%20and%20sleep(2)--+&Submit=Submit"

# Variante simple (peut passer si le score reste < 9)
curl -i "http://<ip_waf>/vulnerabilities/sqli/?id=1' or 1=1-- +&Submit=Submit"

# XSS simple
curl -i "http://<ip_waf>/?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E"

# Double encodage
curl -i "http://<ip_waf>/?q=%2527%2520or%25201%253d1"
```

## Dashboard & logs
- Tableau auto-refresh (2 s) avec filtres `severity`, `action`, `rule`, `limit`.
- Bouton **Refresh** pour recharger immédiatement.
- Nouveau bouton **Clear logs** pour vider `data/logs.json` depuis l'interface.

## Structure rapide du code
- `waf/config.py`: configuration (ports, backend, seuils).
- `waf/proxy.py`: reverse proxy + scoring + décision IDS/IPS.
- `waf/logger.py`: JSON Lines dans `data/logs.json`.
- `waf/dashboard_app.py`: API `/api/logs` et `/api/logs/clear` + templating.
- `waf/templates/` & `waf/static/`: dashboard web.
- `deploy_kali.sh`: déploiement Kali automatisé (venv + services systemd).
