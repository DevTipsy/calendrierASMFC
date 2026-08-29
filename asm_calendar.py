#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère asmonaco.ics à partir du calendrier officiel AS Monaco.
Source : https://www.asmonaco.com/fr/pros/calendrier
Parsing basé sur les composants HTML réels (MatchPresentationCard).
"""

import re
import sys
import html
import hashlib
import datetime as dt
import urllib.request
import urllib.parse

URL = "https://www.asmonaco.com/fr/pros/calendrier"
OUT = "asmonaco.ics"
TZ = "Europe/Paris"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

COMP = {"L1": "Ligue 1", "UCF": "UEFA Conference League"}

# Coordonnées GPS précises des stades (lat, lon) + adresse complète pour LOCATION.
# Ça permet à iOS d'ouvrir Plans exactement sur le bon point via la propriété GEO,
# sans dépendre du géocodage approximatif d'un simple nom de stade.
STADES = {
    "Stade Louis-II": (43.727677, 7.415611, "Stade Louis-II, 7 Avenue des Castelans, 98000 Monaco"),
    "Parc des Princes": (48.841389, 2.253056, "Parc des Princes, 24 Rue du Commandant Guilbaud, 75016 Paris"),
    "Stade de la Meinau": (48.559722, 7.755556, "Stade de la Meinau, 12 Rue de l'Extenwoerth, 67100 Strasbourg"),
    "Stade du Moustoir - Yves Allainmat": (47.734444, -3.373889, "Stade du Moustoir, Boulevard Léo Le Bourgo, 56100 Lorient"),
    "Stade Jean Bouin": (48.841944, 2.253333, "Stade Jean-Bouin, 26 Avenue du Général Sarrail, 75016 Paris"),
    "Stade Marie-Marvingt": (47.999722, 0.204722, "Stade Marie-Marvingt, Avenue Pierre de Coubertin, 72100 Le Mans"),
    "Stade de l'Abbé Deschamps": (47.792778, 3.566389, "Stade de l'Abbé-Deschamps, 4 Boulevard de Verdun, 89000 Auxerre"),
    "Groupama Stadium": (45.765278, 4.982083, "Groupama Stadium, 10 Avenue Simone Veil, 69150 Décines-Charpieu"),
    "Stade de l'Aube": (48.309167, 4.091389, "Stade de l'Aube, 12 Boulevard Vitry, 10000 Troyes"),
    "Stade Brestois 29": (48.404722, -4.475556, "Stade Francis-Le Blé, 2 Rue de Quimper, 29200 Brest"),
    "Stade Francis-Le Blé": (48.404722, -4.475556, "Stade Francis-Le Blé, 2 Rue de Quimper, 29200 Brest"),
    "Stade Rennais FC": (48.107500, -1.712778, "Roazhon Park, Route de Lorient, 35000 Rennes"),
    "Roazhon Park": (48.107500, -1.712778, "Roazhon Park, Route de Lorient, 35000 Rennes"),
    "Orange Vélodrome": (43.269722, 5.395833, "Orange Vélodrome, 3 Boulevard Michelet, 13008 Marseille"),
    "Stade Raymond Kopa": (47.464722, -0.523889, "Stade Raymond-Kopa, Rue de la Rabière, 49000 Angers"),
    "Decathlon Arena - Stade Pierre-Mauroy": (50.611944, 3.130556, "Decathlon Arena - Stade Pierre-Mauroy, 261 Boulevard de Tournai, 59650 Villeneuve-d'Ascq"),
    "Stadium de Toulouse": (43.583056, 1.434167, "Stadium de Toulouse, 1 Allée Gabriel Tinaud, 31400 Toulouse"),
    "Allianz Riviera": (43.705278, 7.192500, "Allianz Riviera, Boulevard des Jardiniers, 06200 Nice"),
    "Stade Bollaert-Delelis": (50.432500, 2.815278, "Stade Bollaert-Delelis, 27 Rue Georges Berne, 62300 Lens"),
}

CARD_RE = re.compile(r'data-component="MatchPresentationCard".*?</nxp-full-countdown>?.*?matchPresCardTeams.*?(?=data-component="MatchPresentationCard"|matchPresCardList|</ul>|$)', re.S)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def title_case(t):
    # "AS MONACO" -> "AS Monaco" ; garde les sigles courts en majuscules
    t = html.unescape(t).strip()
    if t.upper() == "AS MONACO":
        return "AS Monaco"
    words = []
    for w in t.split():
        if len(w) <= 3 and w.isupper():      # OGC, PSG, RC, FC, OL...
            words.append(w)
        else:
            words.append(w.capitalize())
    return " ".join(words)


def parse(h):
    events = []
    # découpe grossière : chaque carte commence à data-component="MatchPresentationCard"
    parts = h.split('data-component="MatchPresentationCard"')[1:]
    for p in parts:
        dm = re.search(r'datetime="([\d]{4})-([\d]{2})-([\d]{2}) ([\d]{2}):([\d]{2})', p)
        if not dm:
            continue
        y, mo, d, hh, mi = map(int, dm.groups())

        comp_m = re.search(r'data-competition="([^"]+)"', p[:200]) \
                 or re.search(r'data-competition="([^"]+)"',
                              h[h.find(p[:80]) - 200: h.find(p[:80])] if p[:80] in h else "")
        # data-competition est AVANT le datetime dans la même balise div : on le récupère en amont
        comp_code = None
        pre = h.split('data-component="MatchPresentationCard"')
        # plus simple : chercher la compétition dans le <p> du bloc
        cm = re.search(r'<p>\s*([^<]+?)\s*<br>', p)
        comp_label = html.unescape(cm.group(1)).strip() if cm else "AS Monaco"

        # stade = 2e ligne du <p>
        sm = re.search(r'<br>\s*([^<]+?)\s*</p>', p)
        stade = html.unescape(sm.group(1)).strip() if sm else ""

        passed = 'data-passed="true"' in p[:120]

        teams = re.findall(r'matchPresCardTeamName">([^<]+)<', p)
        if len(teams) >= 2:
            home, away = title_case(teams[0]), title_case(teams[1])
            summary = f"{home} vs {away}"
        else:
            summary = comp_label

        start = dt.datetime(y, mo, d, hh, mi)
        uid = hashlib.md5(f"{start.isoformat()}|{summary}".encode()).hexdigest() + "@asmonaco"
        events.append({
            "start": start, "summary": summary, "location": stade,
            "desc": comp_label, "uid": uid, "passed": passed,
        })
    return events


def esc(s):
    return (s.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    # RFC 5545 : une ligne de contenu ne doit pas dépasser 75 octets ;
    # au-delà, on la replie avec CRLF + un espace en début de ligne suivante.
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    parts = []
    i = 0
    limit = 75
    while i < len(b):
        end = min(i + limit, len(b))
        # ne pas couper au milieu d'un caractère UTF-8 multi-octets
        while end < len(b) and end > i and (b[end] & 0xC0) == 0x80:
            end -= 1
        parts.append(b[i:end].decode("utf-8"))
        i = end
        limit = 74  # une ligne de continuation commence par un espace (compté dans les 75)
    return ("\r\n ").join(parts)


def geo_stade(stade):
    # Coordonnées GPS + adresse connue -> LOCATION précis et bouton Itinéraire fiable sur iOS.
    # Repli sur le nom brut si le stade n'est pas dans la table (iOS géocodera le texte,
    # Plans en priorité, sinon Google/autre selon les réglages du téléphone).
    return STADES.get(stade)


def to_ics(events):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//tipsy//ASMonaco//FR",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:AS Monaco",
         f"X-WR-TIMEZONE:{TZ}", "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
         "X-PUBLISHED-TTL:PT12H"]
    for e in events:
        s = e["start"]; end = s + dt.timedelta(hours=2)
        geo = geo_stade(e["location"])
        location_txt = geo[2] if geo else e["location"]
        ev = ["BEGIN:VEVENT", f"UID:{e['uid']}", f"DTSTAMP:{now}",
              f"DTSTART;TZID={TZ}:{s.strftime('%Y%m%dT%H%M%S')}",
              f"DTEND;TZID={TZ}:{end.strftime('%Y%m%dT%H%M%S')}",
              f"SUMMARY:{esc(e['summary'])}",
              f"LOCATION:{esc(location_txt)}"]
        if geo:
            lat, lon, addr = geo
            ev.append(f"GEO:{lat:.6f};{lon:.6f}")
        ev += [f"DESCRIPTION:{esc(e['desc'])}",
               "BEGIN:VALARM", "TRIGGER:-PT1H", "ACTION:DISPLAY",
               "DESCRIPTION:Match AS Monaco dans 1h", "END:VALARM", "END:VEVENT"]
        L += ev
    L.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in L) + "\r\n"


def main():
    events = parse(fetch(URL))
    if not events:
        print("Aucun match trouvé — structure du site changée.", file=sys.stderr)
        sys.exit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(to_ics(events))
    print(f"OK: {len(events)} matchs -> {OUT}")


if __name__ == "__main__":
    main()
