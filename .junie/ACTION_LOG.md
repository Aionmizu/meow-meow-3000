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
