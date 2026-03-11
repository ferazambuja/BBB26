#!/usr/bin/env python3
"""
Scrape GShow BBB 26 agenda (programacao do dia) for a given date.

The agenda page is client-rendered (React), so we use a headless browser
(Python Playwright) to extract the schedule after JavaScript loads.

IMPORTANT: Date offset
  The URL at /agenda/YYYY-MM-DD.ghtml covers events from the PREVIOUS day.
  Example: /agenda/2026-03-05.ghtml -> "Aconteceu no BBB 26 no dia 04 de marco"
  The --date argument is the EVENT date (what happened), not the URL date.
  The script adds +1 day automatically to build the correct URL.

Requirements:
  pip install playwright
  python -m playwright install chromium

Usage:
  # What happened on March 4?
  python scripts/scrape_gshow_agenda.py 2026-03-04

  # Range of event dates
  python scripts/scrape_gshow_agenda.py --start 2026-03-01 --end 2026-03-05

  # With JSON output
  python scripts/scrape_gshow_agenda.py 2026-03-04 --json

  # Use static HTML only (no browser, limited output)
  python scripts/scrape_gshow_agenda.py 2026-03-04 --static

Output: docs/scraped/agenda/agenda_YYYY-MM-DD.md (+ .json with --json)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "scraped" / "agenda"
AGENDA_BASE_URL = "https://gshow.globo.com/realities/bbb/bbb-26/agenda"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BBB26-scraper/1.0; +https://github.com/BBB26)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# JS extraction code run inside the browser via page.evaluate().
# This runs in the DOM context — it must be JavaScript regardless of the driver.
_EXTRACT_JS = r"""
() => {
    const result = {heading: '', summary: '', sections: [], timestamp: ''};
    const timeRe = /(\d{1,2}h\d{0,2})/;
    const periodRe = /(No período da (?:manhã|tarde)|A partir de \d{1,2}h\d{0,2})/;

    const h1 = document.querySelector('.agenda-summary-description__title, h1');
    if (h1) result.heading = h1.textContent.trim();

    const summaryP = document.querySelector('.agenda-summary-description__text');
    if (summaryP) result.summary = summaryP.textContent.trim();

    const container = document.querySelector('#agenda-automatizada-template');
    if (!container) return result;

    // Highlight (pinned item, before accordions)
    const highlight = container.querySelector('.event-content-url__isDestaque');
    if (highlight) {
      const titleEl = highlight.querySelector('[class*="titleDefault"]');
      const durationEl = highlight.querySelector('[class*="iconWrapper__type"]');
      const linkEl = highlight.querySelector('a[href]');
      if (titleEl) {
        result.sections.push({
          label: 'Destaque',
          time: '',
          items: [{
            title: titleEl.textContent.trim(),
            duration: durationEl ? durationEl.textContent.trim() : '',
            href: linkEl ? linkEl.href : '',
            isLive: false,
          }]
        });
      }
    }

    // Walk MUI Accordions — each has a summary (label+time) and region (items)
    const seen = new Set();
    container.querySelectorAll('[class*="MuiAccordion-root"]').forEach(acc => {
      const summary = acc.querySelector('[class*="MuiAccordionSummary-content"]');
      const region = acc.querySelector('[class*="MuiAccordion-region"]');
      if (!summary || !region) return;

      const items = [];
      region.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        if (!href.includes('gshow.globo.com') && !href.includes('globoplay.globo.com')) return;
        let title = '';
        const titleEl = a.querySelector('[class*="titleDefault"]');
        if (titleEl) title = titleEl.textContent.trim();
        if (!title) title = a.textContent.trim();
        title = title.replace(/^\d+\s*(?:min|seg|h)\s*/i, '').trim();
        if (!title || title.length < 10) return;
        if (seen.has(href)) return;
        seen.add(href);

        const durationEl = a.querySelector('[class*="iconWrapper__type"]');
        const isLive = (a.textContent || '').includes('AO VIVO');
        title = title.replace(/^AO VIVO\s*/i, '').trim();

        items.push({
          title,
          duration: durationEl ? durationEl.textContent.trim() : '',
          href,
          isLive,
        });
      });

      if (items.length === 0) return;

      const rawLabel = summary.textContent.trim();
      let label = rawLabel;
      let time = '';

      const descRe = /(Durante o programa|Após a Eliminação|No período da (?:manhã|tarde)|A partir de \d{1,2}h\d{0,2})/;
      const dMatch = rawLabel.match(descRe);
      if (dMatch) {
        time = dMatch[1];
        label = rawLabel.replace(dMatch[1], '').trim();
      } else {
        const pMatch = rawLabel.match(periodRe);
        if (pMatch) {
          time = pMatch[1];
          label = rawLabel.replace(pMatch[1], '').trim();
        } else {
          const tMatch = rawLabel.match(timeRe);
          if (tMatch) {
            time = tMatch[1];
            label = rawLabel.replace(tMatch[1], '').trim();
          }
        }
      }

      const key = label + '|' + time;
      if (seen.has('section:' + key)) return;
      seen.add('section:' + key);

      result.sections.push({label, time, items});
    });

    const text = container.textContent || '';
    const tsMatch = text.match(/atualizado\s+([\d/]+\s+[^\s]+\s+[\d:]+\s+[AP]M)/i);
    if (tsMatch) result.timestamp = tsMatch[1];

    return result;
}
"""


def agenda_url(event_date: str) -> str:
    """Build agenda URL. The URL date is event_date + 1 day."""
    dt = datetime.strptime(event_date, "%Y-%m-%d") + timedelta(days=1)
    return f"{AGENDA_BASE_URL}/{dt.strftime('%Y-%m-%d')}.ghtml"


def scrape_agenda_playwright(event_date: str) -> dict:
    """
    Scrape agenda using Python Playwright headless browser (renders JavaScript).

    Requires: pip install playwright && python -m playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Python playwright not installed.\n"
            "Run: pip install playwright && python -m playwright install chromium\n"
            "Or use --static mode for basic extraction."
        )

    url = agenda_url(event_date)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(8000)
            raw = page.evaluate(_EXTRACT_JS)
        finally:
            browser.close()

    # Flatten sections into a schedule list with section/time metadata
    schedule = []
    for section in raw.get("sections", []):
        label = section.get("label", "")
        time_slot = section.get("time", "")
        for item in section.get("items", []):
            schedule.append({
                "section": label,
                "time": time_slot,
                **item,
            })

    return {
        "date": event_date,
        "url": url,
        "heading": raw.get("heading", ""),
        "summary": raw.get("summary", ""),
        "schedule": schedule,
        "timestamp": raw.get("timestamp", ""),
        "method": "playwright",
    }


def scrape_agenda_static(event_date: str, session: requests.Session | None = None) -> dict:
    """
    Lightweight fallback: fetch static HTML only (title + heading, no schedule).

    The GShow agenda page is client-rendered, so schedule will be empty.
    Use this when Playwright is not available.
    """
    session = session or requests.Session()
    url = agenda_url(event_date)
    resp = session.get(url, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    title = ""
    title_el = soup.find("title")
    if title_el:
        title = re.sub(r"\s+", " ", title_el.get_text()).strip()

    heading = ""
    h1 = soup.find("h1")
    if h1:
        heading = re.sub(r"\s+", " ", h1.get_text()).strip()

    return {
        "date": event_date,
        "url": url,
        "heading": heading,
        "title": title,
        "schedule": [],
        "timestamp": "",
        "method": "static",
    }


def agenda_to_markdown(data: dict) -> str:
    """Render scraped agenda as Markdown."""
    lines = [
        f"# {data.get('heading') or data.get('title') or data['date']}",
        "",
        f"**Fonte:** [{data['url']}]({data['url']})",
        "",
    ]

    if data.get("summary"):
        lines.append(f"> {data['summary']}")
        lines.append("")

    lines.append("---")
    lines.append("")

    schedule = data.get("schedule", [])
    if schedule:
        lines.append("## Programacao do Dia")
        lines.append("")
        current_section = ""
        for item in schedule:
            section = item.get("section", "")
            if section and section != current_section:
                lines.append(f"### {section}")
                lines.append("")
                current_section = section

            time_str = item.get("time", "")
            title = item.get("title", "")
            duration = item.get("duration", "")
            href = item.get("href", "")
            live = " **AO VIVO**" if item.get("isLive") else ""

            time_prefix = f"**{time_str}** " if time_str else ""
            dur_suffix = f" ({duration})" if duration else ""
            if href:
                lines.append(f"- {time_prefix}[{title}]({href}){dur_suffix}{live}")
            else:
                lines.append(f"- {time_prefix}{title}{dur_suffix}{live}")
        lines.append("")
    else:
        lines.append("*Programacao nao disponivel (pagina renderizada por JavaScript).*")
        lines.append("*Use sem --static para extrair via Playwright.*")
        lines.append("")

    if data.get("timestamp"):
        lines.append(f"*Atualizado: {data['timestamp']}*")
        lines.append("")

    return "\n".join(lines)


def parse_date(s: str) -> str:
    """Validate and return YYYY-MM-DD."""
    dt = datetime.strptime(s.strip(), "%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape GShow BBB 26 agenda for one or more EVENT dates.\n"
            "The date you provide is WHAT HAPPENED (event date), not the URL date.\n"
            "The script auto-adjusts the URL (+1 day) to match GShow's convention."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/scrape_gshow_agenda.py 2026-03-04\n"
            "  python scripts/scrape_gshow_agenda.py --start 2026-03-01 --end 2026-03-05 --json\n"
            "  python scripts/scrape_gshow_agenda.py 2026-03-04 --static  # no browser needed\n"
        ),
    )
    parser.add_argument(
        "dates", nargs="*", metavar="YYYY-MM-DD",
        help="Event date(s) — what day's events to fetch",
    )
    parser.add_argument("--start", metavar="YYYY-MM-DD", help="Start of date range")
    parser.add_argument("--end", metavar="YYYY-MM-DD", help="End of date range (inclusive)")
    parser.add_argument(
        "-o", "--output", default=str(DEFAULT_OUTPUT_DIR), metavar="DIR",
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--json", action="store_true", help="Also write .json per date")
    parser.add_argument(
        "--static", action="store_true",
        help="Use static HTML only (no browser, limited output)",
    )
    args = parser.parse_args()

    # Build date list
    dates = []
    for d in (args.dates or []):
        try:
            dates.append(parse_date(d))
        except ValueError:
            print(f"Error: invalid date {d!r}; use YYYY-MM-DD", file=sys.stderr)
            return 1
    if args.start and args.end:
        try:
            start = datetime.strptime(parse_date(args.start), "%Y-%m-%d")
            end = datetime.strptime(parse_date(args.end), "%Y-%m-%d")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if start > end:
            print("Error: --start must be <= --end", file=sys.stderr)
            return 1
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
    if not dates:
        parser.print_help(sys.stderr)
        return 1

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    errors = 0

    for event_date in dates:
        try:
            if args.static:
                data = scrape_agenda_static(event_date, session)
            else:
                data = scrape_agenda_playwright(event_date)
        except Exception as e:
            print(f"Failed {event_date}: {e}", file=sys.stderr)
            errors += 1
            continue

        n_events = len(data.get("schedule", []))
        method = data.get("method", "?")
        print(f"{event_date}: {n_events} events ({method})", file=sys.stderr)

        md = agenda_to_markdown(data)
        md_path = out_dir / f"agenda_{event_date}.md"
        md_path.write_text(md, encoding="utf-8")

        if args.json:
            json_path = out_dir / f"agenda_{event_date}.json"
            json_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
