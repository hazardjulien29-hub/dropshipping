# Dropshipping — paramétrage de l’analyse

Ce dépôt sert à **connecter** n8n, Airtable et Shopify pour que l’agent puisse auditer ton automatisation.

Il n’y a pas encore de boutique ni de workflows dans Git : on pose d’abord les accès.

## Par où commencer

Fais **les deux** si tu peux : exports **et** APIs. Les exports suffisent pour un premier audit. Les APIs permettent de relire le live (workflows actifs, tables, commandes).

1. Lis [docs/parametrage.md](docs/parametrage.md) (clics exacts).
2. Dépose les fichiers dans `exports/` (voir ci-dessous).
3. Crée les clés, puis vérifie :

```bash
cp .env.example .env
# remplis .env
python3 scripts/check_connections.py
```

Sur Cursor Cloud, ajoute les **mêmes noms de variables** dans [Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents) puis relance un agent.

## Où mettre les fichiers

| Dossier | Contenu |
|---|---|
| `exports/n8n/` | JSON des workflows (menu `…` → Download) |
| `exports/airtable/` | CSV de chaque table |
| `exports/shopify/` | Notes, liste d’apps, export thème si tu en as un |
| `exports/captures/` | Screenshots (admin, ads, fournisseur, etc.) |

Si un CSV contient des **noms / emails / adresses clients**, ne le commite pas : envoie-le dans le chat.

## Inventaire

Complète [stack/inventaire.md](stack/inventaire.md) : URL boutique, n8n, fournisseur, ads, email.

## Sécurité

- Jamais de mot de passe de compte dans Git ni dans le chat.
- Tokens **lecture seule** uniquement.
- Un `.env` local n’est pas versionné (voir `.gitignore`).
