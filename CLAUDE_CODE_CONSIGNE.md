# Consigne pour Claude Code — Déploiement calendrier AS Monaco auto-update

## Objectif
Créer et pousser un repo Git qui scrape le calendrier officiel de l'AS Monaco,
génère un fichier `.ics`, et le republie automatiquement toutes les 12h via
GitHub Actions. Le but final : pouvoir s'abonner à l'URL depuis l'app Calendrier
iPhone avec resync automatique.

## Contexte
- Repo distant déjà créé (ou à créer) : `git@github.com:DevTipsy/calendrierASMFC.git`
- Branche cible : `main`
- Source scrapée : https://www.asmonaco.com/fr/pros/calendrier
- Le HTML du site expose des composants `MatchPresentationCard` avec :
  - `<time datetime="YYYY-MM-DD HH:MM:SS...">` (ISO 8601, fuseau inclus)
  - `data-competition="L1"` ou `"UCF"`
  - `matchPresCardTeamName` (2 par carte : domicile puis extérieur)
  - stade dans le `<p>` après `<br>`
- 34 matchs attendus à ce jour (peut évoluer).

## Étapes à exécuter

### 1. Créer les fichiers
Crée exactement ces 4 fichiers (contenus fournis ci-dessous dans ce dossier) :
- `asm_calendar.py` — le scraper (stdlib pure, aucune dépendance)
- `.github/workflows/update.yml` — le cron GitHub Actions
- `README.md` — la doc
- `asmonaco.ics` — généré par `python3 asm_calendar.py` (ne pas écrire à la main)

### 2. Tester le scraper en local
```bash
python3 asm_calendar.py
# Doit afficher "OK: N matchs -> asmonaco.ics" (N ~ 34)
# Vérifier : grep -c "BEGIN:VEVENT" asmonaco.ics
```
Si 0 match : la structure du site a changé, adapter les regex de `parse()`.

### 3. Init + commit + push
```bash
git init
git add -A
git commit -m "init: calendrier ASM auto-update"
git branch -M main
git remote add origin git@github.com:DevTipsy/calendrierASMFC.git
git push -u origin main
```
Si le remote existe déjà et refuse (repo non vide) : `git pull --rebase origin main` puis re-push.

### 4. Réglages GitHub (via gh CLI si dispo, sinon indiquer à l'utilisateur)
Si `gh` est authentifié :
```bash
# Activer les permissions d'écriture pour Actions
gh api -X PUT repos/DevTipsy/calendrierASMFC/actions/permissions/workflow \
  -f default_workflow_permissions=write

# Activer GitHub Pages sur la branche main (dossier root)
gh api -X POST repos/DevTipsy/calendrierASMFC/pages \
  -f "source[branch]=main" -f "source[path]=/" 2>/dev/null || \
gh api -X PUT repos/DevTipsy/calendrierASMFC/pages \
  -f "source[branch]=main" -f "source[path]=/"

# Lancer le workflow une première fois
gh workflow run "Update ASM calendar" --repo DevTipsy/calendrierASMFC
```
Si `gh` n'est pas dispo/authentifié, afficher à l'utilisateur les 3 réglages manuels :
1. Settings → Actions → General → Workflow permissions → Read and write
2. Settings → Pages → branche `main`, dossier `/root`
3. Onglet Actions → Run workflow

### 5. Donner l'URL finale à l'utilisateur
```
URL d'abonnement : https://devtipsy.github.io/calendrierASMFC/asmonaco.ics
Sur iPhone : Réglages → Apps → Calendrier → Comptes → Ajouter un compte →
Autre → Ajouter un calendrier avec abonnement → coller l'URL
(remplacer https:// par webcal:// si besoin)
```

## Vérification finale
- [ ] `asmonaco.ics` présent sur la branche main
- [ ] Workflow visible dans l'onglet Actions et exécuté au moins 1x en vert
- [ ] Pages actif → l'URL `.../asmonaco.ics` renvoie bien le fichier (curl -sI doit donner 200)
- [ ] `curl -s https://devtipsy.github.io/calendrierASMFC/asmonaco.ics | grep -c BEGIN:VEVENT` > 0

## Notes
- Le workflow ne commit que s'il y a un changement (`git commit || echo "aucun changement"`).
- Le cron tourne en UTC.
- Aucune dépendance pip : le scraper utilise uniquement la stdlib Python 3.12.
