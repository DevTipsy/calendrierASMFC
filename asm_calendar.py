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


def itineraire_urls(stade):
    # Plans (Apple Maps) en priorité, Google Maps en repli.
    q = urllib.parse.quote(stade)
    apple = f"https://maps.apple.com/?q={q}"
    google = f"https://www.google.com/maps/search/?api=1&query={q}"
    return apple, google


def to_ics(events):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//tipsy//ASMonaco//FR",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:AS Monaco",
         f"X-WR-TIMEZONE:{TZ}", "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
         "X-PUBLISHED-TTL:PT12H"]
    for e in events:
        s = e["start"]; end = s + dt.timedelta(hours=2)
        desc = e["desc"]
        if e["location"]:
            apple, google = itineraire_urls(e["location"])
            desc += f"\nItinéraire (Plans) : {apple}\nItinéraire (Google Maps) : {google}"
        L += ["BEGIN:VEVENT", f"UID:{e['uid']}", f"DTSTAMP:{now}",
              f"DTSTART;TZID={TZ}:{s.strftime('%Y%m%dT%H%M%S')}",
              f"DTEND;TZID={TZ}:{end.strftime('%Y%m%dT%H%M%S')}",
              f"SUMMARY:{esc(e['summary'])}",
              f"LOCATION:{esc(e['location'])}",
              f"DESCRIPTION:{esc(desc)}",
              "BEGIN:VALARM", "TRIGGER:-PT1H", "ACTION:DISPLAY",
              "DESCRIPTION:Match AS Monaco dans 1h", "END:VALARM", "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"


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
