#!/usr/bin/env python3
"""
Penn State Bulletin Scraper
===========================
Scrapes program requirements and course descriptions from bulletins.psu.edu
and saves structured JSON to backend/data/.

Usage:
  python backend/scraper/bulletin_scraper.py                   # full run
  python backend/scraper/bulletin_scraper.py --programs-only   # programs only
  python backend/scraper/bulletin_scraper.py --courses-only    # courses only
  python backend/scraper/bulletin_scraper.py --college engineering  # one college
  python backend/scraper/bulletin_scraper.py --dept cmpsc,math      # specific depts
  python backend/scraper/bulletin_scraper.py --force-fetch          # ignore cache

Output files (backend/data/):
  programs.json      — array of program objects
  courses.json       — array of course objects
  departments.json   — dept code → name index
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# Allow running from repo root or from backend/scraper/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scraper.fetcher import fetch, BASE_URL
from backend.scraper.parsers.program_parser import parse_program_page
from backend.scraper.parsers.course_parser import parse_department_page, parse_department_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# ── College discovery ─────────────────────────────────────────────────────────

COLLEGES_URL = "/undergraduate/colleges/"

def get_all_colleges(force: bool = False) -> list[dict]:
    """Return [{slug, name, url}] for every college."""
    soup = fetch(BASE_URL + COLLEGES_URL, force=force)
    if not soup:
        logger.error("Could not fetch colleges index")
        return []

    colleges = []
    content = soup.find("div", id="content") or soup.find("div", id="textcontainer")
    if content:
        for a in content.find_all("a", href=True):
            href = a["href"]
            m = re.match(r"/undergraduate/colleges/([^/]+)/?$", href)
            if m:
                slug = m.group(1)
                colleges.append({
                    "slug": slug,
                    "name": a.get_text(strip=True),
                    "url": BASE_URL + href,
                })
    logger.info("Found %d colleges", len(colleges))
    return colleges


# ── Program discovery ─────────────────────────────────────────────────────────

def get_programs_for_college(college_slug: str, force: bool = False) -> list[dict]:
    """Return [{name, url}] for every program listed on a college page."""
    url = f"{BASE_URL}/undergraduate/colleges/{college_slug}/"
    soup = fetch(url, force=force)
    if not soup:
        logger.warning("Could not fetch college page: %s", college_slug)
        return []

    programs = []
    content = soup.find("div", id="content") or soup.find("div", id="textcontainer")
    if not content:
        content = soup  # fallback

    for a in content.find_all("a", href=True):
        href = a["href"]
        # Program URLs are deeper: /undergraduate/colleges/{college}/{program}/
        m = re.match(rf"/undergraduate/colleges/{re.escape(college_slug)}/([^/]+)/?$", href)
        if m:
            programs.append({
                "name": a.get_text(strip=True),
                "url": BASE_URL + href,
                "college": college_slug,
            })

    logger.info("  College %s: %d programs found", college_slug, len(programs))
    return programs


# ── Program scraping ──────────────────────────────────────────────────────────

def scrape_programs(
    college_filter: str | None = None,
    force: bool = False,
) -> list[dict]:
    """
    Scrape all program pages (or just one college if college_filter is set).
    Returns deduplicated list of program dicts.
    """
    colleges = get_all_colleges(force=force)
    if college_filter:
        colleges = [c for c in colleges if c["slug"] == college_filter]
        if not colleges:
            logger.error("College slug '%s' not found. Available: %s",
                         college_filter, [c["slug"] for c in get_all_colleges()])
            return []

    all_programs: list[dict] = []
    seen_urls: set[str] = set()

    for college in colleges:
        logger.info("College: %s", college["name"])
        programs_list = get_programs_for_college(college["slug"], force=force)

        for prog_ref in programs_list:
            url = prog_ref["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            logger.info("  Program: %s", prog_ref["name"])
            soup = fetch(url, force=force)
            if not soup:
                logger.warning("    SKIP (fetch failed): %s", url)
                continue

            parsed = parse_program_page(soup, url, college["slug"])
            if parsed:
                all_programs.append(parsed)
            else:
                logger.warning("    SKIP (parse failed): %s", url)

    logger.info("Total programs scraped: %d", len(all_programs))
    return all_programs


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate_programs(programs: list[dict]) -> list[dict]:
    """
    Some programs have the same curriculum across campuses.
    Merge by (program_name, plan_codes) — combine campus lists.
    """
    seen: dict[str, dict] = {}
    for prog in programs:
        key = (prog["program_name"], tuple(sorted(prog.get("plan_codes", []))))
        if key in seen:
            existing = seen[key]
            # Merge campuses
            existing_campuses = set(existing.get("campuses", []))
            new_campuses = set(prog.get("campuses", []))
            existing["campuses"] = sorted(existing_campuses | new_campuses)
        else:
            seen[key] = prog

    result = list(seen.values())
    logger.info("After deduplication: %d programs", len(result))
    return result


# ── Course scraping ───────────────────────────────────────────────────────────

def get_all_departments(force: bool = False) -> list[dict]:
    """Return [{code, name, slug, url}] for every department."""
    url = BASE_URL + "/university-course-descriptions/undergraduate/"
    soup = fetch(url, force=force)
    if not soup:
        logger.error("Could not fetch course catalog index")
        return []
    depts = parse_department_index(soup)
    logger.info("Found %d departments", len(depts))
    return depts


def scrape_courses(
    dept_filter: list[str] | None = None,
    force: bool = False,
) -> tuple[list[dict], list[dict]]:
    """
    Scrape all course descriptions (or filtered departments).
    Returns (courses, departments) tuple.
    """
    depts = get_all_departments(force=force)
    if dept_filter:
        filter_set = {d.lower() for d in dept_filter}
        depts = [d for d in depts if d["slug"].lower() in filter_set or d["code"].lower() in filter_set]
        if not depts:
            logger.error("No matching departments for filter: %s", dept_filter)
            return [], []

    all_courses: list[dict] = []

    for dept in depts:
        logger.info("Department: %s (%s)", dept["name"], dept["code"])
        soup = fetch(dept["url"], force=force)
        if not soup:
            logger.warning("  SKIP (fetch failed): %s", dept["url"])
            continue

        courses = parse_department_page(soup, dept["code"])
        all_courses.extend(courses)

    logger.info("Total courses scraped: %d", len(all_courses))
    return all_courses, depts


# ── Output ────────────────────────────────────────────────────────────────────

def save_json(data: object, filename: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %s (%d items)", path, len(data) if isinstance(data, list) else 1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Penn State Bulletin Scraper — build programs.json and courses.json"
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--programs-only", action="store_true",
        help="Only scrape program pages (skip course descriptions)"
    )
    mode.add_argument(
        "--courses-only", action="store_true",
        help="Only scrape course descriptions (skip program pages)"
    )
    p.add_argument(
        "--college", metavar="SLUG",
        help="Scrape only this college (e.g. 'engineering', 'liberal-arts')"
    )
    p.add_argument(
        "--dept", metavar="CODE[,CODE...]",
        help="Scrape only these department codes (e.g. 'cmpsc,math')"
    )
    p.add_argument(
        "--force-fetch", action="store_true",
        help="Ignore cache and re-download all pages"
    )
    p.add_argument(
        "--list-colleges", action="store_true",
        help="Print available college slugs and exit"
    )
    p.add_argument(
        "--list-depts", action="store_true",
        help="Print available department codes and exit"
    )
    return p.parse_args()


def main():
    args = parse_args()
    force = args.force_fetch

    # ── Info modes ────────────────────────────────────────────────────────
    if args.list_colleges:
        colleges = get_all_colleges(force=force)
        for c in colleges:
            print(f"  {c['slug']:<40}  {c['name']}")
        return

    if args.list_depts:
        depts = get_all_departments(force=force)
        for d in depts:
            print(f"  {d['code']:<12}  {d['name']}")
        return

    # ── Programs ──────────────────────────────────────────────────────────
    if not args.courses_only:
        logger.info("=== SCRAPING PROGRAMS ===")
        programs = scrape_programs(
            college_filter=args.college,
            force=force,
        )
        programs = deduplicate_programs(programs)
        save_json(programs, "programs.json")

    # ── Courses ───────────────────────────────────────────────────────────
    if not args.programs_only:
        logger.info("=== SCRAPING COURSES ===")
        dept_filter = [d.strip() for d in args.dept.split(",")] if args.dept else None
        courses, depts = scrape_courses(
            dept_filter=dept_filter,
            force=force,
        )
        save_json(courses, "courses.json")
        # departments index
        dept_index = {d["code"]: d["name"] for d in depts}
        save_json(dept_index, "departments.json")

    logger.info("Done.")


if __name__ == "__main__":
    main()
