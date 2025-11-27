## 2025-11-20 16:40
- Action: Ajout d'un script de déploiement automatisé pour Kali (deploy_kali.sh)
- But: Permettre un déploiement en une seule commande (installe dépendances, clone/maj repo, venv, services systemd, ouverture UFW, vérif /healthz)
- Emplacement: ./deploy_kali.sh
- Services créés: meow-waf.service, meow-waf-dashboard.service
- Paramètres: --repo, --branch, --install-dir, --backend, --mode, --waf-host, --waf-port, --dash-host, --dash-port
- Remarques: orjson est optionnel à l'exécution (fallback JSON std).

## 2025-11-20 16:41
- Action: Documentation de déploiement "One-command" ajoutée dans README
- But: Que l'utilisateur puisse copier-coller une commande sur Kali pour déployer
- Suivant: Push sur GitHub requis pour pouvoir curl le script directement (cf. section README)

## 2025-11-20 17:12
- Action: Ajout d'un script d'aide pour SSH GitHub sous Windows (`scripts/setup_github_ssh.ps1`).
- But: Éliminer l'erreur « Permission denied (publickey) » en automatisant la génération/chargement de clé et en guidant l'ajout dans GitHub.
- Détails: démarre `ssh-agent`, génère une clé `ed25519` si absente, l'ajoute à l'agent, affiche la clé publique.
- Suivant: L'utilisateur ajoute la clé sur https://github.com/settings/ssh/new puis vérifie `ssh -T git@github.com`.

## 2025-11-20 17:12
- Action: Amélioration du script de push (`scripts/push_to_github.ps1`).
- But: Mieux diagnostiquer les erreurs de push SSH et guider vers le script SSH ou l'usage d'un PAT HTTPS.
- Détails: test `ssh -T git@github.com` quand l'URL est `git@github.com:...`, messages guidés.

## 2025-11-20 17:12
- Action: Ajout d'un `.gitignore` pour ignorer `.venv/`, `data/`, `dist/`, etc.
- But: Empêcher l'upload de binaires/données locales et garder un repo propre.

## 2025-11-20 17:12
- Action: Ajout d'une annexe dans README (dépannage « Permission denied (publickey) »).
- But: Étapes claires pour résoudre le problème (SSH ou HTTPS+PAT) avec commandes prêtes à copier.

## 2025-11-21 09:46
- Action: Donnée sensible supprimée à la demande de l'utilisateur.
- Clé publique SSH: [REDACTED AT USER REQUEST]
- Contexte: L'utilisateur a initialement partagé sa clé publique, puis a demandé son retrait du dépôt public.
- Suivant:
  - Ne pas stocker de secrets/clé (même publiques) dans le dépôt.
  - Pour pousser « normalement », utiliser HTTPS avec Git Credential Manager (prompts interactifs).
  - Commande suggérée: `.\\scripts\\push_to_github.ps1 -RemoteUrl "https://github.com/Aionmizu/meow-meow-3000.git" -Branch main -UseCredentialManager`.
  - Déployer sur Kali (one-liner): `curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/deploy_kali.sh | sudo bash`.

## 2025-11-21 10:00
- Action: Correction exécution script de push sous Linux (erreur $'\r' en Bash).
- Problème: `./push_to_github.ps1` lancé depuis Bash sur Kali => erreur CRLF/PowerShell.
- Fix:
  - Ajout `scripts/push_to_github.sh` (équivalent Bash pour Linux/macOS).
  - Ajout shebang `#!/usr/bin/env pwsh` dans les scripts PowerShell (.ps1).
  - Ajout `.gitattributes` pour forcer LF sur *.sh et CRLF sur *.ps1.
  - README mis à jour: sépare clairement les instructions Linux (sh) vs Windows (ps1) + avertissement.
- Utilisation:
  - Linux: `bash scripts/push_to_github.sh --remote https://github.com/Aionmizu/meow-meow-3000.git --branch main`
  - Windows: `.\scripts\push_to_github.ps1 -RemoteUrl "https://github.com/Aionmizu/meow-meow-3000.git" -Branch main -UseCredentialManager`

## 2025-11-21 11:13
- Action: README enrichi avec sections détaillées « Fonctionnalités » et « Règles de gestion ».
- But: Répondre à la demande d’expliciter toutes les fonctionnalités et la logique (normalisation, signatures, scoring, seuils, décisions, logs, en‑têtes).
- Fichiers: README.md (nouvelles sections 13 et 14).
- Impact: Documentation complète pour démonstration/évaluation; aucune modification du comportement applicatif.
- Suivant: Optionnel — ajouter des signatures supplémentaires (ex: `SQLI_BARE_OR_1EQ1`) ou ajuster les seuils selon le niveau d’agressivité souhaité.

## 2025-11-21 11:16
- Action: Renforcement des signatures et ajout d’un script de mise à jour Kali.
- Détails (règles):
  - Ajout: `SQLI_BARE_OR_1EQ1` (4), `SQLI_COMMENT_DASH` (2), `SQLI_STACKED_QUERIES` (4), `PATH_TRAVERSAL` (3), `LFI_WRAPPER` (4), `CMD_INJECTION` (4), `XSS_IMG_ONERROR` (4).
  - Modification: `SQLI_UNION_SELECT` passe de 5 à 6 points.
- Fichiers modifiés/ajoutés: `waf/rules.py`, `scripts/update_kali.sh`, `README.md` (section 15 « Mettre à jour… »).
- Impact: Charges encodées/UNION et vecteurs LFI/Traversal/CMD détectés avec plus de sensibilité; plus de cas atteignent le seuil de blocage par défaut (9).
- Déploiement: Sur Kali, exécuter `sudo bash /opt/meow-meow-3000/scripts/update_kali.sh` ou via GitHub `curl -fsSL https://raw.githubusercontent.com/Aionmizu/meow-meow-3000/main/scripts/update_kali.sh | sudo bash`.

