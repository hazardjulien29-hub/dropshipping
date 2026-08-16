# Paramétrage n8n, Airtable, Shopify, Cursor

Objectif : que l’agent puisse **lire** tes outils. Tu fais les clics une fois ; ensuite `python3 scripts/check_connections.py` confirme que ça marche.

---

## 1. Exports (sans API, 10 minutes)

### n8n

1. Ouvre ton instance n8n (cloud ou self-host).
2. Ouvre **chaque** workflow, surtout la boucle principale.
3. En haut à droite : `…` → **Download** / **Export**.
4. Enregistre les `.json` dans `exports/n8n/`.

Si tu as beaucoup de workflows : `…` sur la liste → export de tout le projet si l’option existe.

### Airtable

1. Ouvre la base dropshipping.
2. Pour **chaque table** : menu de la table `…` → **Download CSV**.
3. Nomme les fichiers clairement : `produits.csv`, `commandes.csv`, `fournisseurs.csv`.
4. Place-les dans `exports/airtable/`.

Le **Base ID** est dans l’URL : `https://airtable.com/appXXXXXXXXXXXXXX/...` → `appXXXXXXXXXXXXXX`. Note-le dans `stack/inventaire.md`.

### Shopify

1. Copie l’URL admin : `https://admin.shopify.com/store/TON-STORE`  
   et le domaine `TON-STORE.myshopify.com`.
2. **Paramètres → Applications et canaux de vente** : capture la liste des apps.
3. **Commandes** : une capture de la file récente (sans coller de données bancaires).
4. Dépose captures et notes dans `exports/shopify/` et `exports/captures/`.

### Autres outils

Même principe dans `exports/captures/` : CJ / Zendrop / AliExpress, Meta Ads, Klaviyo, Sheets, etc.

---

## 2. Cursor sur ton PC (fichiers locaux)

Ça n’ouvre **pas** un contrôle à distance. L’agent local voit le dossier que tu ouvres.

1. Installe [Cursor Desktop](https://cursor.com/download).
2. Clone ce repo (GitHub Desktop, ou `git clone https://github.com/hazardjulien29-hub/dropshipping.git`).
3. **Fichier → Ouvrir un dossier** → le dossier `dropshipping`.
4. Copie tes JSON / CSV / captures dans `exports/`.
5. Dans le chat : *« analyse les fichiers dans exports/ »*.

---

## 3. Clés API (lecture)

Même noms de variables partout : `.env` en local, **et** [Cursor Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents).

Après avoir ajouté des secrets Cloud, **relance un nouvel agent** : les secrets de cette conversation déjà ouverte ne sont pas forcément injectés.

### 3.1 n8n

Docs : [Créer une clé API n8n](https://docs.n8n.io/connect/n8n-api/authentication/).

1. n8n → **Settings** → **n8n API**.
2. **Create an API key**.
3. Label : `cursor-lecture`.
4. Expiration : 90 jours (ou selon toi).
5. Si on te propose des scopes (Enterprise) : `workflow:read`, `workflow:list`, `execution:read`.
6. **Copie la clé tout de suite** (elle ne réapparaît pas).

Variables :

```text
N8N_BASE_URL=https://TON-SOUS-DOMAINE.app.n8n.cloud
N8N_API_KEY=…
```

Sans `/api/v1` à la fin. Self-host : `https://n8n.ton-domaine.com`.

**Si tu ne vois pas « n8n API »** : sur n8n Cloud l’API n’est pas dispo en essai gratuit. Utilise les exports JSON (section 1). En self-host, vérifie que `N8N_PUBLIC_API_DISABLED` n’est pas à `true`.

### 3.2 Airtable

Docs : [Personal access tokens](https://airtable.com/developers/web/guides/personal-access-tokens).

1. Va sur [airtable.com/create/tokens](https://airtable.com/create/tokens).
2. **Create new token**, nom : `cursor-lecture`.
3. Scopes (lecture) :
   - `data.records:read`
   - `schema.bases:read`
4. **Add a base** → uniquement ta base dropshipping (pas « all bases »).
5. Crée, copie le token (`pat…`).

Variables :

```text
AIRTABLE_PAT=pat…
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
```

### 3.3 Shopify (2026)

Shopify n’affiche plus un token `shpat_…` copiable pour les **nouvelles** apps. On crée une app dans le [Dev Dashboard](https://dev.shopify.com/dashboard/), on l’installe sur **ta** boutique, puis le script échange Client ID + Secret contre un token (24 h).

Docs : [Créer une app](https://shopify.dev/docs/apps/build/dev-dashboard/create-apps-using-dev-dashboard) · [Tokens](https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens).

1. [Dev Dashboard](https://dev.shopify.com/dashboard/) → **Apps** → **Create app** → **Start from Dev Dashboard**.
2. Nom : `Cursor analyse dropshipping`.
3. Onglet **Versions** :
   - App URL : `https://shopify.dev/apps/default-app-home` (app non embarquée).
   - Webhooks : version API la plus récente.
   - Scopes (lecture) :
     - `read_products`
     - `read_inventory`
     - `read_locations`
     - `read_orders`
     - `read_fulfillments`
     - `read_merchant_managed_fulfillment_orders`
   - **Release**.
4. **Home** → **Install app** → ta boutique → **Install**.
5. **Settings** de l’app → copie **Client ID** et **Client secret**.

Variables :

```text
SHOPIFY_STORE_DOMAIN=ta-boutique.myshopify.com
SHOPIFY_CLIENT_ID=…
SHOPIFY_CLIENT_SECRET=…
```

Si tu as encore un **ancien** token Admin `shpat_…`, tu peux mettre `SHOPIFY_ADMIN_API_TOKEN` à la place du couple client (le script accepte les deux).

**Erreur `shop_not_permitted`** : le grant « client credentials » marche seulement si l’app et la boutique sont dans **la même organisation** Dev Dashboard. La boutique doit apparaître sous **Dev stores** ou comme store de cette org. Si tu construis pour une autre boutique hors org, ce flux ne marche pas : reste sur les exports.

**Commandes / clients bloqués** : Shopify peut exiger une demande « protected customer data ». Pour l’audit, produits + apps + captures de commandes suffisent souvent.

---

## 4. Vérifier

Localement :

```bash
cp .env.example .env
# colle tes valeurs dans .env
python3 scripts/check_connections.py
```

Le script :

- liste ce qui est déjà dans `exports/` ;
- teste n8n / Airtable / Shopify **seulement** si les variables sont présentes ;
- n’écrit jamais les secrets dans le terminal.

Tu dois voir `OK` sur les services remplis. Colle la sortie (sans tes clés) dans le chat si quelque chose échoue.

---

## 5. Checklist

- [ ] JSON n8n dans `exports/n8n/`
- [ ] CSV Airtable dans `exports/airtable/`
- [ ] URL boutique + captures Shopify
- [ ] `stack/inventaire.md` rempli
- [ ] `N8N_BASE_URL` + `N8N_API_KEY` (si API dispo)
- [ ] `AIRTABLE_PAT` + `AIRTABLE_BASE_ID`
- [ ] `SHOPIFY_STORE_DOMAIN` + Client ID/Secret (ou ancien token)
- [ ] Secrets aussi dans Cursor Cloud, **puis nouvel agent**
- [ ] `python3 scripts/check_connections.py` → OK

Ensuite : *« analyse les exports et les connexions API »*.
