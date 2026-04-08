#!/usr/bin/env python3
"""
Coachella 2026 – ICS Calendar Generator
========================================
Generates one .ics file per stage, covering both weekends.
Run manually or via GitHub Actions on a schedule.

Outputs to: ../calendars/<stage-slug>.ics
"""

import os
import re
import hashlib
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# ── Timezone ──────────────────────────────────────────────────────────────────
PT = ZoneInfo("America/Los_Angeles")

# ── Venue ─────────────────────────────────────────────────────────────────────
VENUE = "Empire Polo Club\\, 81-800 Avenue 51\\, Indio\\, CA 92201"
FESTIVAL_URL = "https://www.coachella.com"

# ── Date bases ────────────────────────────────────────────────────────────────
WEEKEND1_DATES = {
    "Friday":   "2026-04-10",
    "Saturday": "2026-04-11",
    "Sunday":   "2026-04-12",
}
WEEKEND2_DATES = {
    "Friday":   "2026-04-17",
    "Saturday": "2026-04-18",
    "Sunday":   "2026-04-19",
}

# ── Stage metadata ────────────────────────────────────────────────────────────
STAGES = {
    "Coachella Stage":  {"slug": "coachella-stage",  "emoji": "🎤"},
    "Outdoor Theatre":  {"slug": "outdoor-theatre",  "emoji": "🌙"},
    "Sahara":           {"slug": "sahara",            "emoji": "🔊"},
    "Mojave":           {"slug": "mojave",            "emoji": "🎸"},
    "Gobi":             {"slug": "gobi",              "emoji": "🎶"},
    "Quasar":           {"slug": "quasar",            "emoji": "🌀"},
    "Do LaB":           {"slug": "do-lab",            "emoji": "🌿"},
}

# ── Schedule data ─────────────────────────────────────────────────────────────
# Format: (artist, stage, start_HH:MM, end_HH:MM, next_day_end, headliner)
# next_day_end=True means end time crosses midnight into the next calendar day
# Weekend 2 mirrors Weekend 1 times; the GitHub Action re-runs to pick up
# any official changes when they're announced.

SCHEDULE = {
    # ── WEEKEND 1 ──────────────────────────────────────────────────────────────
    ("W1", "Friday"): [
        ("Slayyyter",           "Mojave",           "15:00", "15:45", False, False),
        ("Lykke Li",            "Outdoor Theatre",  "17:20", "18:10", False, False),
        ("Teddy Swims",         "Coachella Stage",  "17:30", "18:20", False, False),
        ("Central Cee",         "Mojave",           "17:30", "18:15", False, False),
        ("The xx",              "Coachella Stage",  "19:00", "19:55", False, False),
        ("KATSEYE",             "Sahara",           "20:00", "20:45", False, False),
        ("Moby",                "Mojave",           "20:10", "21:00", False, False),
        ("Holly Humberstone",   "Gobi",             "20:25", "21:10", False, False),
        ("Sabrina Carpenter",   "Coachella Stage",  "21:05", "22:35", False, True),
        ("Ethel Cain",          "Mojave",           "22:35", "23:25", False, False),
        ("Disclosure",          "Outdoor Theatre",  "22:35", "23:50", False, False),
        ("Swae Lee",            "Sahara",           "22:50", "23:40", False, False),
        ("Blood Orange",        "Mojave",           "23:55", "00:45", True,  False),
        ("Anyma",               "Coachella Stage",  "00:00", "01:30", True,  False),
        ("Sexyy Red",           "Sahara",           "00:05", "00:55", True,  False),
    ],
    ("W1", "Saturday"): [
        ("Jack White",          "Mojave",           "15:00", "15:45", False, False),
        ("Addison Rae",         "Coachella Stage",  "17:30", "18:20", False, False),
        ("Giveon",              "Coachella Stage",  "19:00", "19:50", False, False),
        ("Sombr",               "Outdoor Theatre",  "19:05", "19:55", False, False),
        ("Labrinth",            "Outdoor Theatre",  "20:30", "21:25", False, False),
        ("PinkPantheress",      "Mojave",           "20:55", "21:45", False, False),
        ("BIA",                 "Gobi",             "21:00", "21:45", False, False),
        ("David Guetta",        "Quasar",           "21:00", "23:00", False, False),
        ("Interpol",            "Mojave",           "22:15", "23:15", False, False),
        ("David Byrne",         "Outdoor Theatre",  "22:20", "23:20", False, False),
        ("Justin Bieber",       "Coachella Stage",  "23:25", "01:00", True,  True),
    ],
    ("W1", "Sunday"): [
        ("Gigi Perez",          "Outdoor Theatre",  "16:00", "16:45", False, False),
        ("Little Simz",         "Mojave",           "16:25", "17:10", False, False),
        ("Wet Leg",             "Coachella Stage",  "16:45", "17:30", False, False),
        ("Clipse",              "Outdoor Theatre",  "17:15", "18:10", False, False),
        ("Major Lazer",         "Coachella Stage",  "18:10", "19:10", False, False),
        ("Foster the People",   "Outdoor Theatre",  "18:45", "19:40", False, False),
        ("Iggy Pop",            "Mojave",           "19:10", "20:10", False, False),
        ("Young Thug",          "Coachella Stage",  "19:50", "20:40", False, False),
        ("Fatboy Slim",         "Quasar",           "20:00", "22:00", False, False),
        ("Laufey",              "Outdoor Theatre",  "20:40", "21:40", False, False),
        ("FKA twigs",           "Mojave",           "20:45", "22:00", False, False),
        ("Karol G",             "Coachella Stage",  "21:55", "23:30", False, True),
        ("Kaskade",             "Sahara",           "22:45", "23:55", False, False),
    ],

    # ── WEEKEND 2 ──────────────────────────────────────────────────────────────
    # Seeded as mirrors of W1. GitHub Action overwrites these when official
    # W2 times are published (detected via schedule change on coachella.com).
    ("W2", "Friday"): [
        ("Slayyyter",           "Mojave",           "15:00", "15:45", False, False),
        ("Lykke Li",            "Outdoor Theatre",  "17:20", "18:10", False, False),
        ("Teddy Swims",         "Coachella Stage",  "17:30", "18:20", False, False),
        ("Central Cee",         "Mojave",           "17:30", "18:15", False, False),
        ("The xx",              "Coachella Stage",  "19:00", "19:55", False, False),
        ("KATSEYE",             "Sahara",           "20:00", "20:45", False, False),
        ("Moby",                "Mojave",           "20:10", "21:00", False, False),
        ("Holly Humberstone",   "Gobi",             "20:25", "21:10", False, False),
        ("Sabrina Carpenter",   "Coachella Stage",  "21:05", "22:35", False, True),
        ("Ethel Cain",          "Mojave",           "22:35", "23:25", False, False),
        ("Disclosure",          "Outdoor Theatre",  "22:35", "23:50", False, False),
        ("Swae Lee",            "Sahara",           "22:50", "23:40", False, False),
        ("Blood Orange",        "Mojave",           "23:55", "00:45", True,  False),
        ("Anyma",               "Coachella Stage",  "00:00", "01:30", True,  False),
        ("Sexyy Red",           "Sahara",           "00:05", "00:55", True,  False),
    ],
    ("W2", "Saturday"): [
        ("Jack White",          "Mojave",           "15:00", "15:45", False, False),
        ("Addison Rae",         "Coachella Stage",  "17:30", "18:20", False, False),
        ("Giveon",              "Coachella Stage",  "19:00", "19:50", False, False),
        ("Sombr",               "Outdoor Theatre",  "19:05", "19:55", False, False),
        ("Labrinth",            "Outdoor Theatre",  "20:30", "21:25", False, False),
        ("PinkPantheress",      "Mojave",           "20:55", "21:45", False, False),
        ("BIA",                 "Gobi",             "21:00", "21:45", False, False),
        ("David Guetta",        "Quasar",           "21:00", "23:00", False, False),
        ("Interpol",            "Mojave",           "22:15", "23:15", False, False),
        ("David Byrne",         "Outdoor Theatre",  "22:20", "23:20", False, False),
        ("Justin Bieber",       "Coachella Stage",  "23:25", "01:00", True,  True),
    ],
    ("W2", "Sunday"): [
        ("Gigi Perez",          "Outdoor Theatre",  "16:00", "16:45", False, False),
        ("Little Simz",         "Mojave",           "16:25", "17:10", False, False),
        ("Wet Leg",             "Coachella Stage",  "16:45", "17:30", False, False),
        ("Clipse",              "Outdoor Theatre",  "17:15", "18:10", False, False),
        ("Major Lazer",         "Coachella Stage",  "18:10", "19:10", False, False),
        ("Foster the People",   "Outdoor Theatre",  "18:45", "19:40", False, False),
        ("Iggy Pop",            "Mojave",           "19:10", "20:10", False, False),
        ("Young Thug",          "Coachella Stage",  "19:50", "20:40", False, False),
        ("Fatboy Slim",         "Quasar",           "20:00", "22:00", False, False),
        ("Laufey",              "Outdoor Theatre",  "20:40", "21:40", False, False),
        ("FKA twigs",           "Mojave",           "20:45", "22:00", False, False),
        ("Karol G",             "Coachella Stage",  "21:55", "23:30", False, True),
        ("Kaskade",             "Sahara",           "22:45", "23:55", False, False),
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_dt(date_str: str, time_str: str, next_day: bool = False) -> datetime:
    """Return a timezone-aware datetime in PT."""
    y, mo, d = map(int, date_str.split("-"))
    h, m = map(int, time_str.split(":"))
    dt = datetime(y, mo, d, h, m, 0, tzinfo=PT)
    if next_day:
        dt += timedelta(days=1)
    return dt


def uid(artist: str, stage: str, weekend: str, day: str) -> str:
    raw = f"{artist}-{stage}-{weekend}-{day}-coachella2026"
    return hashlib.md5(raw.encode()).hexdigest() + "@coachella2026.ics"


def fold(line: str) -> str:
    """RFC 5545 line folding at 75 octets."""
    out, buf = [], ""
    for ch in line:
        if len((buf + ch).encode("utf-8")) > 75:
            out.append(buf)
            buf = " " + ch
        else:
            buf += ch
    out.append(buf)
    return "\r\n".join(out)


def escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fmt_dt(dt: datetime) -> str:
    """Format as TZID-based local time per RFC 5545."""
    return dt.strftime("%Y%m%dT%H%M%S")


def build_vevent(artist, stage, start_dt, end_dt, weekend, day, headliner, emoji):
    label = "★ HEADLINER – " if headliner else ""
    summary = f"{emoji} {label}{artist} @ {stage}"
    description = (
        f"Artist: {artist}\\n"
        f"Stage: {stage}\\n"
        f"Weekend: {weekend.replace('W1','Weekend 1').replace('W2','Weekend 2')}\\n"
        f"Day: {day}\\n"
        f"Coachella 2026 – Empire Polo Club\\, Indio CA\\n"
        f"Official site: {FESTIVAL_URL}"
    )
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid(artist, stage, weekend, day)}",
        f"DTSTAMP:{now_utc}",
        f"DTSTART;TZID=America/Los_Angeles:{fmt_dt(start_dt)}",
        f"DTEND;TZID=America/Los_Angeles:{fmt_dt(end_dt)}",
        f"SUMMARY:{escape(summary)}",
        f"DESCRIPTION:{escape(description)}",
        f"LOCATION:{VENUE}",
        f"URL:{FESTIVAL_URL}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
    ]
    return "\r\n".join(fold(l) for l in lines)


def build_ics(stage: str, events: list[str], slug: str) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    header = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Coachella 2026//Stage Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Coachella 2026 – {stage}",
        f"X-WR-CALDESC:All sets on the {stage} – Coachella 2026 (both weekends). Auto-updated.",
        "X-WR-TIMEZONE:America/Los_Angeles",
        "BEGIN:VTIMEZONE",
        "TZID:America/Los_Angeles",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:-0800",
        "TZOFFSETTO:-0700",
        "TZNAME:PDT",
        "DTSTART:19700308T020000",
        "RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:-0700",
        "TZOFFSETTO:-0800",
        "TZNAME:PST",
        "DTSTART:19701101T020000",
        "RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11",
        "END:STANDARD",
        "END:VTIMEZONE",
    ])
    body = "\r\n".join(events)
    footer = "END:VCALENDAR"
    return header + "\r\n" + body + "\r\n" + footer + "\r\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def generate():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "calendars")
    os.makedirs(out_dir, exist_ok=True)

    # Collect events per stage
    stage_events: dict[str, list[str]] = {s: [] for s in STAGES}

    for (weekend, day), sets in SCHEDULE.items():
        date_map = WEEKEND1_DATES if weekend == "W1" else WEEKEND2_DATES
        base_date = date_map[day]

        for (artist, stage, start_t, end_t, next_day_end, headliner) in sets:
            if stage not in STAGES:
                print(f"  ⚠  Unknown stage '{stage}' for {artist} – skipping")
                continue

            # Handle midnight-crossing starts (already next day in source)
            start_next = int(start_t.split(":")[0]) < 13 and day != "Friday" or \
                         (start_t in ("00:00", "00:05") and weekend)
            # Simpler: if hour < 12 treat as next-day for late night sets
            sh = int(start_t.split(":")[0])
            start_is_next = sh < 12 and day in ("Friday", "Saturday")

            start_dt = make_dt(base_date, start_t, next_day=start_is_next)
            end_dt   = make_dt(base_date, end_t,   next_day=(start_is_next or next_day_end))

            # Sanity: end must be after start
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

            emoji = STAGES[stage]["emoji"]
            vevent = build_vevent(artist, stage, start_dt, end_dt, weekend, day, headliner, emoji)
            stage_events[stage].append(vevent)

    # Write one .ics per stage
    written = []
    for stage, events in stage_events.items():
        if not events:
            continue
        slug = STAGES[stage]["slug"]
        ics_content = build_ics(stage, events, slug)
        path = os.path.join(out_dir, f"{slug}.ics")
        with open(path, "w", encoding="utf-8") as f:
            f.write(ics_content)
        print(f"  ✓  {path}  ({len(events)} events)")
        written.append(slug)

    print(f"\nDone – {len(written)} calendar files written.")
    return written


if __name__ == "__main__":
    generate()
