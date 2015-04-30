# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from collections import defaultdict
from decimal import Decimal
import json
import os
import re

from bs4 import BeautifulSoup
import requests


def read_json(path):
    with open(path, 'r') as f:
        return json.loads(f.read())


def plaintext_parser(v):
    return v


def length_parser(v):
    match = re.match('^(?P<length>\d+([.,]\d+)?) ?(км|km)?$', v)
    if match is None:
        return None
    return Decimal(match.group('length').replace(',', '.'))


def ascent_parser(v):
    match = re.match('^(\((?P<direction>изкачване|спускане)\))? *[:–-]? *(?P<ascent>-?\d+([.,]\d+)?) ?(м|m)?$', v)
    if match is None:
        return None
    result = Decimal(match.group('ascent').replace(',', '.'))
    direction = match.group('direction')
    if direction == 'спускане':
        result = -result
    return result


def strenuousness_parser(v):
    match = re.match('.*КФН=(?P<strenuousness>\d+).*', v)
    if match is None:
        return None
    return int(match.group('strenuousness'))


def difficulty_parser(v):
    # Replace cyrillic T with latin T, because R is already latin.
    v = v.replace('Т', 'T')
    return sorted(set(re.findall('(R1|R2|R3|T1|T2|T3|T4|T5|FX|F|X)', v)),
                  key=lambda x: difficulty_parser.sort_order.index(x))


def terrain_parser(v):
    v = v.lower().replace('т1', 't1').replace('т2', 't2').replace(
        'т3', 't3').replace('т4', 't4').replace('т5', 't5')
    match = re.findall('(-|–)? ?(?P<terrain>(асфалт|черни пътища|пътеки) ' +
                       '?(r1|r2|r3|t1|t2|t3|t4|t5|fx|f|x)?) ?' +
                       '(-|–)? ?~? ?(?P<length>\d+([.,]?\d+) ?) ?(км|km)?', v)
    if not match:
        return None
    return match


difficulty_parser.sort_order = ['R1', 'R2', 'R3', 'T1', 'T2', 'T3', 'T4', 'T5', 'F', 'X', 'FX']

keys = {
    'изходна точка': 'trailhead',
    'дължина': 'length',
    'денивелация': 'ascent',
    'изкачване': 'ascent',
    'продължителност': 'duration',
    'вода': 'water',
    'храна': 'food',
    'терен': 'terrain',
    'ниво на техническа трудност': 'difficulty',
    'физическо натоварване': 'strenuousness',
}
parsers = {
    'trailhead': plaintext_parser,
    'length': length_parser,
    'ascent': ascent_parser,
    'duration': plaintext_parser,
    'water': plaintext_parser,
    'food': plaintext_parser,
    'terrain': terrain_parser,
    'difficulty': difficulty_parser,
    'strenuousness': strenuousness_parser,
}
exec_root = os.path.dirname(__file__)


def download_page(url):
    dest = os.path.join(exec_root, 'html_cache',
                        os.path.basename(url) + '.html')
    if os.path.exists(dest):
        with open(dest, 'r') as f:
            return f.read().decode('utf-8')
    print('Downloading', url)
    with open(dest, 'w') as f:
        page = requests.get(url)
        page.raise_for_status()
        f.write(page.text.encode('utf-8'))
    return download_page(url)


def split_meta_strings(strings):
    parts = defaultdict(list)
    current_key = None
    for s in strings:
        norm_s = s.lower().strip(' :')
        if norm_s in keys:
            current_key = keys[norm_s]
        elif current_key:
            parts[current_key].append(s)
    return {k: ' '.join(v) for k, v in parts.items()}


def parse_meta_parts(meta_parts):
    parsed_meta = {}
    for k, v in meta_parts.items():
        if k in parsers:
            parsed_value = parsers[k](v)
            if parsed_value:
                parsed_meta[k] = parsed_value
            else:
                print('Parser for {0} failed on {1} returning {2}'.format(k, v, repr(parsed_value)))
        else:
            print('Missing parser for {0}'.format(k))
    return parsed_meta


def find_metas(soup):
    metas = []
    for p in soup.find_all('p'):
        strings = list(re.sub('[ ]+', ' ', t) for t in p.stripped_strings)
        if 'Изходна точка:' in strings or 'Дължина:' in strings or 'Продължителност:' in strings:
            meta_parts = split_meta_strings(strings)
            parsed_meta = parse_meta_parts(meta_parts)
            metas.append(parsed_meta)
    return metas


def find_trace_links(soup):
    links = []
    for a in soup.find_all('a'):
        href = a.get('href')
        if not href:
            continue
        if not href.endswith('.zip') and not href.endswith('.gpx'):
            continue
        if 'нарязани до 500' in a.text.lower():
            continue
        links.append(href)
    return links


def parse_page(url, content, ignore_errors):
    if len(content) == 0:
        raise Exception('Empty HTML file!')
    # print('Parsing', url)
    soup = BeautifulSoup(content)
    parsed_metas = find_metas(soup)
    # print(parsed_metas)
    trace_links = find_trace_links(soup)
    # print(trace_links)
    if len(trace_links) != 1:
        print('Error parsing {0}: {1} links found, must be exactly 1.'.format(url, len(trace_links)))
        return None
    if not ignore_errors and len(parsed_metas) != 1:
        print('Error parsing {0}; {1} metadata blocks found, must be exactly 1'.format(
            url, len(parsed_metas)))
        return None
    parsed_meta = parsed_metas[0] if len(parsed_metas) else None
    return parsed_meta, trace_links[0]


def read_routes():
    input_routes = read_json(os.path.join(exec_root, '..', 'preprocessor', 'input.json'))
    return {r['link']: r for r in input_routes['routes']}


def main():
    pages_ignore = {}
    routes = read_routes()
    with open(os.path.join(exec_root, 'pages_exceptions.txt')) as f:
        for line in f:
            parts = line.decode('utf-8').strip().split(': ', 2)
            pages_ignore[parts[2]] = parts[1]
    with open(os.path.join(exec_root, 'pages.txt')) as f:
        for rel_url in f:
            rel_url = rel_url.decode('utf-8').strip()
            exception = pages_ignore.get(rel_url)
            if exception == 'ignore':
                continue
            url = u'http://mtb-bg.com' + rel_url.strip()
            content = download_page(url)
            parse_page(url, content, exception == 'include')


if __name__ == '__main__':
    main()
