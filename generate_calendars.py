#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")
TIME_RE = re.compile(r"(?<!\d)(\d{2}:\d{2}|--\s*:\s*--)(?!\d)")
MATCH_RE = re.compile(r"(.+?)\s+VS\s+(.+?)(?=\s+LALIGA\b)", re.I)
COMP_RE = re.compile(r"(LALIGA\s+(?:EA SPORTS|HYPERMOTION))", re.I)

@dataclass(frozen=True)
class Match:
    match_date: date
    kickoff: time | None
    home: str
    away: str
    competition: str
    broadcaster: str | None
    source_url: str

def normalized_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.cells, self.parts = [], [], []
        self.in_row = self.in_cell = False
        self.link = None
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.in_row, self.cells, self.link = True, [], None
        elif tag in {"td", "th"} and self.in_row: self.in_cell, self.parts = True, []
        elif tag == "a" and self.in_row and self.link is None: self.link = dict(attrs).get("href")
    def handle_data(self, data):
        if self.in_cell: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            self.cells.append(normalized_text(" ".join(self.parts))); self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append((self.cells, self.link)); self.in_row = False

def parse_matches(html: str, page_url: str) -> list[Match]:
    parser = TableParser(); parser.feed(html); matches = []
    for cells, link in parser.rows:
        row = normalized_text(" ".join(cells))
        date_hit, match_hit, comp_hit = DATE_RE.search(row), MATCH_RE.search(row), COMP_RE.search(row)
        if not (date_hit and match_hit and comp_hit): continue
        time_hit = TIME_RE.search(row)
        kickoff = None if not time_hit or "--" in time_hit.group(1) else datetime.strptime(time_hit.group(1), "%H:%M").time()
        home = DATE_RE.sub("", match_hit.group(1)); home = TIME_RE.sub("", home)
        home = re.sub(r"^(?:LUN|MAR|MIE|MIÉ|JUE|VIE|SAB|SÁB|DOM)\s+", "", home, flags=re.I)
        broadcaster = None
        if len(cells) >= 5 and cells[4] not in {"", "-"}:
            broadcaster = cells[4].replace("Horario peninsular", "").strip(" ,-—") or None
        matches.append(Match(datetime.strptime(date_hit.group(1), "%d.%m.%Y").date(), kickoff,
            normalized_text(home), normalized_text(match_hit.group(2)), normalized_text(comp_hit.group(1).upper()),
            broadcaster, urljoin(page_url, link) if link else page_url))
    if not matches: raise ValueError("LaLiga no devolvió partidos reconocibles; puede haber cambiado su HTML")
    return matches

def stable_uid(match: Match) -> str:
    season = match.match_date.year if match.match_date.month >= 7 else match.match_date.year - 1
    raw = f"{season}|{match.competition}|{match.home}|{match.away}".casefold()
    return f"{hashlib.sha256(raw.encode()).hexdigest()[:24]}@laliga-calendars"

def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fold(line: str) -> str:
    chunks, current = [], ""
    for char in line:
        if len((current + char).encode()) > 73: chunks.append(current); current = " " + char
        else: current += char
    chunks.append(current); return "\r\n".join(chunks)

def make_calendar(matches: list[Match], club: dict, config: dict) -> bytes:
    tz, stamp = ZoneInfo(config["timezone"]), datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LaLiga club calendars//ES", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(club['calendar_name'])}", f"X-WR-TIMEZONE:{config['timezone']}", f"X-APPLE-CALENDAR-COLOR:{club['color']}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT24H", "X-PUBLISHED-TTL:PT24H"]
    for match in matches:
        home_game = match.home.casefold() == club["name"].casefold()
        summary = f"{'🏠' if home_game else '✈️'} {match.home} – {match.away}" + (" · Horario por confirmar" if not match.kickoff else "")
        lines += ["BEGIN:VEVENT", f"UID:{stable_uid(match)}", f"DTSTAMP:{stamp}", f"LAST-MODIFIED:{stamp}", f"SUMMARY:{escape(summary)}"]
        if match.kickoff:
            start = datetime.combine(match.match_date, match.kickoff, tzinfo=tz); end = start + timedelta(minutes=config["duration_minutes"])
            lines += [f"DTSTART;TZID={config['timezone']}:{start:%Y%m%dT%H%M%S}", f"DTEND;TZID={config['timezone']}:{end:%Y%m%dT%H%M%S}", "TRANSP:OPAQUE"]
            for minutes in config["alerts_minutes_before"]:
                lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{escape(club['short_name'] + ' juega pronto')}", f"TRIGGER:-PT{minutes}M", "END:VALARM"]
        else:
            lines += [f"DTSTART;VALUE=DATE:{match.match_date:%Y%m%d}", f"DTEND;VALUE=DATE:{match.match_date + timedelta(days=1):%Y%m%d}", "TRANSP:TRANSPARENT"]
        details = [f"Condición: {'Casa' if home_game else 'Fuera'}", f"Competición: {match.competition}"]
        if match.broadcaster: details.append(f"Televisión: {match.broadcaster}")
        if not match.kickoff: details.append("Fecha provisional y horario pendiente de confirmación por LaLiga.")
        details.append(f"Fuente oficial: {match.source_url}")
        lines += [f"DESCRIPTION:{escape(chr(10).join(details))}", f"URL:{match.source_url}",
            f"CATEGORIES:{escape(club['name'])},{escape(match.competition)},{'Casa' if home_game else 'Fuera'}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(fold(line) for line in lines) + "\r\n").encode()

def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; LaLigaCalendar/1.0)"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8")

def main() -> int:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8")); output = ROOT / "docs"; output.mkdir(exist_ok=True); status = {}
    for club in config["clubs"]:
        matches = parse_matches(fetch_html(club["url"]), club["url"])
        matches = [m for m in matches if club["name"].casefold() in {m.home.casefold(), m.away.casefold()}]
        if not matches: raise ValueError(f"No se encontraron partidos de {club['name']}")
        path = output / f"{club['slug']}.ics"; path.write_bytes(make_calendar(matches, club, config))
        status[club["slug"]] = {"events": len(matches), "updated_at": datetime.now().isoformat()}
        print(f"{club['name']}: {len(matches)} eventos -> {path}")
    (output / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc: print(f"ERROR: {exc}", file=sys.stderr); raise
