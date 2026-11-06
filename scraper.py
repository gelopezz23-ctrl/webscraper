#!/usr/bin/env python3

import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import chain

import requests

URL = 'https://www.scrapethissite.com/pages/forms/'
HEADERS = {'User-Agent': 'hockey-scraper/1.0'}

ROW = re.compile(r'<tr class="team">(.*?)</tr>', re.S)
CELL = r'<td class="{}[^"]*">\s*(.*?)\s*</td>'


def fetch(page):
    """Return the HTML of one page of the table."""
    response = requests.get(URL, params={'page_num': page}, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.text


def last_page(text):
    """Pure function: find the highest page number in the pagination links."""
    numbers = map(int, re.findall(r'page_num=(\d+)', text))
    return max(numbers, default=1)


def cell(name, row):
    match = re.search(CELL.format(name), row, re.S)
    return html.unescape(match.group(1)) if match else ''


def parse(row):
    """Pure function: one table row's HTML in, one team dict out."""
    return {
        'name': cell('name', row),
        'year': int(cell('year', row)),
        'wins': int(cell('wins', row) or 0),
        'losses': int(cell('losses', row) or 0),
        'goals_for': int(cell('gf', row) or 0),
        'goals_against': int(cell('ga', row) or 0),
    }


def scrape(page):
    """Page number in, list of team dicts out. Returns [] if the request fails."""
    try:
        return list(map(parse, ROW.findall(fetch(page))))
    except requests.RequestException as error:
        print(f'page {page}: {error}')
        return []


def run(pages, workers):
    """Scrape all pages with the given worker count; return (teams, seconds)."""
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        teams = list(chain.from_iterable(executor.map(scrape, pages)))
    return teams, time.perf_counter() - start


def main():
    pages = range(1, last_page(fetch(1)) + 1)
    print(f'Found {len(pages)} pages.\n')

    timings = {}
    for workers in (1, 8, 24):
        teams, seconds = run(pages, workers)
        timings[workers] = seconds

    print(f'Scraped {len(teams)} team seasons.')

    print('\nTop 5 seasons by wins:')
    for t in sorted(teams, key=lambda t: t['wins'], reverse=True)[:5]:
        print(f'  {t["wins"]:>3} wins  {t["name"]} ({t["year"]})')

    print('\nTop 5 seasons by goal differential:')
    diff = lambda t: t['goals_for'] - t['goals_against']
    for t in sorted(teams, key=diff, reverse=True)[:5]:
        print(f'  {diff(t):>+4}  {t["name"]} ({t["year"]})')

    print()
    for workers, seconds in timings.items():
        print(f'{workers} worker(s): {seconds:.3f} seconds')


if __name__ == '__main__':
    main()