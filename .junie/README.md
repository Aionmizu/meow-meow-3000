# .junie — Suivi de projet (WAF + IDS + Dashboard)

Ce répertoire contient la documentation de suivi pour t’auto‑mettre à jour pendant le développement.

Contenu prévu :
- ACTION_LOG.md — journal des actions réalisées (horodatées), décisions, TODO.
- Notes, checklists, captures et liens utiles.

Règles d’usage :
1. Après chaque modification significative du code ou de la config, ajoute une entrée dans `ACTION_LOG.md` (date, ce qui a été fait, pourquoi, ce qu’il reste).
2. Lorsque tu déploies sur Kali, note la commande exacte, le port, et l’IP backend DVWA utilisée.
3. Garde la même structure de journaux en JSON Lines pour les logs d’exécution (dans `data/logs.json`).
4. Mets ici les extraits de commandes `uv` et `curl` utilisées en classe pour que tout soit reproductible.

Objectif :
- Disposer d’un suivi clair et consultable rapidement, sans polluer le README principal.
