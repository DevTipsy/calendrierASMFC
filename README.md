# Calendrier AS Monaco → iCal auto-update

Scrape le [calendrier officiel](https://www.asmonaco.com/fr/pros/calendrier),
génère `asmonaco.ics`, et le republie toutes les 12h via GitHub Actions.
Abonne ton iPhone à l'URL → resync automatique.

## Déploiement

1. Crée un repo **public** sur GitHub (ex. `asm-calendar`).
2. Pousse ces fichiers (voir commandes plus bas).
3. Repo → **Settings → Pages** → Source: `Deploy from a branch`, branche `main`, dossier `/root` → Save.
4. Repo → **Settings → Actions → General** → Workflow permissions → **Read and write** → Save.
5. Onglet **Actions** → lance `Update ASM calendar` une fois à la main (`Run workflow`).

## URL d'abonnement iPhone

    https://<TON_USER>.github.io/<TON_REPO>/asmonaco.ics

Sur iPhone : **Réglages → Apps → Calendrier → Comptes → Ajouter un compte →
Autre → Ajouter un calendrier avec abonnement** → colle l'URL (remplace `https://` par `webcal://`).

iOS resynchronise seul (intervalle réglable : Récupérer les données).

## Test local

    python3 asm_calendar.py   # -> asmonaco.ics

Aucune dépendance externe (stdlib uniquement).
