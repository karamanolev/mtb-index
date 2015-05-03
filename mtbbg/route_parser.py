# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from collections import defaultdict
from decimal import Decimal
import json
import os
import re

from bs4 import BeautifulSoup
import requests

from utils import parse_decimal


def read_json(path):
    with open(path, 'r') as f:
        return json.loads(f.read(), parse_float=Decimal, parse_int=Decimal)


def plaintext_parser(v):
    return v


def length_parser(v):
    match = re.match('^(?P<length>\d+([.,]\d+)?) ?(км|km)?$', v)
    if match is None:
        return None
    return parse_decimal(match.group('length'))


def unnecessary_false_parser(value):
    s = re.sub('[^a-zа-я]', '', value.lower())
    if s in ['неенеобходима']:
        return False
    return value


def ascent_parser(v):
    match = re.match(
        '^(\((?P<direction>изкачване|спускане)\))? *[:–-]? *(?P<ascent>-?\d+([.,]\d+)?) ?(м|m)?$',
        v)
    if match is None:
        return None
    result = parse_decimal(match.group('ascent'))
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
    matches = re.finditer('(-|–)? ?(?P<terrain>(асфалт|черни пътища|пътеки)' +
                          '( (r1|r2|r3|t1|t2|t3|t4|t5|fx|f|x))?) ?' +
                          '(-|–)? ?~? ?(?P<length>\d+([.,]?\d+) ?)' +
                          ' ?(км|km)?', v)
    result = [
        {
            'terrain': m.group('terrain'),
            'length': parse_decimal(m.group('length')),
        }
        for m in matches
    ]
    return result or None


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
    'water': unnecessary_false_parser,
    'food': unnecessary_false_parser,
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
    warnings = []
    for k, v in meta_parts.items():
        if k in parsers:
            parsed_value = parsers[k](v)
            if parsed_value:
                parsed_meta[k] = parsed_value
            else:
                warnings.append(
                    'Parser for {0} failed on {1} returning {2}'.format(
                        k, v, repr(parsed_value)))
        else:
            warnings.append('Missing parser for {0}'.format(k))
    return parsed_meta, warnings


def find_metas(soup):
    metas = []
    for p in soup.find_all('p'):
        strings = list(re.sub('[ ]+', ' ', t) for t in p.stripped_strings)
        if 'Изходна точка:' in strings or 'Дължина:' in strings or 'Продължителност:' in strings:
            meta_parts = split_meta_strings(strings)
            parse_results = parse_meta_parts(meta_parts)
            metas.append(parse_results)
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
        links.append('http://mtb-bg.com' + href)
    return links


def find_name(soup):
    result = None
    for title in soup.find_all('a', attrs={'class': 'contentpagetitle'}):
        if result is None:
            result = title.get_text(strip=True)
        else:
            return None
    return result


def parse_page(url, content, ignore_errors):
    if len(content) == 0:
        raise Exception('Empty HTML file!')
    # print('Parsing', url)
    soup = BeautifulSoup(content)
    parse_results = find_metas(soup)
    trace_links = find_trace_links(soup)
    parse_warnings = [result[1] for result in parse_results]
    if len(trace_links) == 0:
        parse_warnings.append(
            'Error parsing {0}: no links.'.format(url, len(trace_links)))
        return None, parse_warnings
    if not ignore_errors and len(parse_results) != 1:
        parse_warnings.append(
            'Error parsing {0}; {1} metadata blocks found, must be exactly 1'.format(
                url, len(parse_results)))
        return None, parse_warnings
    parsed_meta = parse_results[0][0] if len(parse_results) else None
    parsed_meta['name'] = find_name(soup)
    parsed_meta['link'] = url
    parsed_meta['traces'] = trace_links
    return parsed_meta, parse_warnings


def read_routes():
    input_routes = read_json(os.path.join(exec_root, '..', 'preprocessor', 'input.json'))
    return {r['link']: r for r in input_routes['routes']}


def compare_routes(old_routes, new_routes):
    old_links = set(old_routes.keys())
    new_links = set(new_routes.keys())
    for link in new_links - old_links:
        print('New route', link)
    for link in old_links - new_links:
        print('Deleted route', link)
    for link in old_links & new_links:
        old_route = old_routes[link]
        new_route = new_routes[link]
        print('Matched route', link)
        old_route_keys = set(old_route.keys())
        new_route_keys = set(new_route.keys())
        for key in old_route_keys | new_route_keys:
            old_value = old_route.get(key)
            new_value = new_route.get(key)
            if old_value != new_value:
                print(' - {0}: {1} != {2}'.format(key, old_value, new_value))


def main():
    pages_ignore = {}
    online_routes = {}
    saved_routes = read_routes()
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
            route, warnings = parse_page(url, content, exception == 'include')
            if route is not None:
                online_routes[url] = route
    compare_routes(saved_routes, online_routes)


if __name__ == '__main__':
    main()
