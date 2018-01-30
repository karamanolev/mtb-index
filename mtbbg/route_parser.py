# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import copy
import locale
import os
import re
from collections import defaultdict
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pytz import timezone

from utils import parse_decimal, ParseResultFix, write_json, read_json, BS4_PARSER


def plaintext_parser(v):
    return v


def length_parser(v):
    if '/' in v:
        v = v.split('/')[0].strip()
    match = re.match('^(?P<length>\d+([.,]\d+)?) ?(км|km)?$', v)
    if match is None:
        return None
    return parse_decimal(match.group('length'))


def unnecessary_false_parser(value):
    s = re.sub('[^a-zа-я]', '', value.lower())
    if s in ['неенеобходима', 'няманужда']:
        return False
    return value


def water_parser(value):
    if unnecessary_false_parser(value) is False:
        return False
    match = re.match('^(?P<water>\d+([.,]\d+)?) ?(л(итра)?)?.?$', value)
    if match is None:
        return value
    return parse_decimal(match.group('water'))


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
    'терен': 'terrains',
    'ниво на техническа трудност': 'difficulty',
    'физическо натоварване': 'strenuousness',
}
parsers = {
    'trailhead': plaintext_parser,
    'length': length_parser,
    'ascent': ascent_parser,
    'duration': plaintext_parser,
    'water': water_parser,
    'food': unnecessary_false_parser,
    'terrains': terrain_parser,
    'difficulty': difficulty_parser,
    'strenuousness': strenuousness_parser,
}
exec_root = os.path.dirname(__file__)


def download_page(url):
    dest = os.path.join(exec_root, 'html_cache',
                        os.path.basename(url) + '.html')
    if os.path.exists(dest):
        with open(dest, 'r') as f:
            return f.read()
    print('Downloading', url)
    with open(dest, 'w') as f:
        page = requests.get(url)
        page.raise_for_status()
        f.write(page.text)
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
            if parsed_value is not None:
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


def parse_date(value):
    locale.setlocale(locale.LC_TIME, 'bg_BG.UTF-8')
    date_str = value.lower()
    return datetime.strptime(date_str, '%A, %d %B %Y %H:%M')


def find_date(soup):
    article_date = None
    for date_elem in soup.find_all('span', attrs={'class': 'createdate'}):
        if article_date is not None:
            return None
        article_date = parse_date(date_elem.get_text(strip=True))
    article_date.replace(tzinfo=timezone('Europe/Sofia'))
    return article_date.isoformat()


def parse_page(url, content, ignore_errors):
    if len(content) == 0:
        raise Exception('Empty HTML file: {}!'.format(url))
    soup = BeautifulSoup(content, BS4_PARSER)
    route = {
        'name': find_name(soup),
        'date': find_date(soup),
        'link': url,
    }
    if route['name'] is None:
        return None, ['Error parsing {0}: name not found.'.format(url)]
    if route['date'] is None:
        return None, ['Error parsing {0}: date not found.'.format(url)]
    parse_results = find_metas(soup)
    trace_links = find_trace_links(soup)
    parse_warnings = [warning for result in parse_results for warning in result[1]]
    if len(trace_links) == 0:
        parse_warnings.append(
            'Error parsing {0}: no links.'.format(url, len(trace_links)))
        return None, parse_warnings
    if not ignore_errors and len(parse_results) != 1:
        parse_warnings.append(
            'Error parsing {0}; {1} metadata blocks found, must be exactly 1'.format(
                url, len(parse_results)))
        return None, parse_warnings
    if len(parse_results):
        route.update(parse_results[0][0])
    route['traces'] = trace_links
    return route, parse_warnings


def read_routes():
    input_routes = read_json(os.path.join(exec_root, '..', 'preprocessor', 'input.json'))
    if len(set(r['name'] for r in input_routes['routes'])) != len(input_routes['routes']):
        print('Duplicate route names in input.json. Can\'t process.')
    return {r['name']: r for r in input_routes['routes']}


def write_routes(routes):
    route_list = list(routes.values())
    route_list.sort(key=lambda r: (r['date'], r['name']))
    data = {
        'routes': route_list,
    }
    write_json(os.path.join(exec_root, '..', 'preprocessor', 'input.json'), data, {
        'indent': '  ',
        'item_sort_key': lambda i: [
            'name', 'date', 'link', 'terrain', 'length', 'ascent',
            'difficulty', 'strenuousness', 'duration', 'water', 'food',
            'terrains', 'traces', 'routes', 'trailhead'].index(i[0]),
        'ensure_ascii': False,
    })


def compare_routes(old_routes, new_routes, exceptions):
    ignored_links = set(k for k, v in exceptions.items() if v == 'ignore')
    old_names = set(old_routes.keys())
    new_names = set(new_routes.keys())
    for name in new_names - old_names:
        if new_routes[name]['link'] in ignored_links:
            continue

        def action(routes):
            routes[name] = new_routes[name]

        yield ParseResultFix(name, ' - New route added', action)
    for name in old_names - new_names:
        if old_routes[name]['link'] in ignored_links:
            continue

        def action(routes):
            del routes[name]

        yield ParseResultFix(name, ' - Route deleted', action)
    for name in old_names & new_names:
        if new_routes[name]['link'] in ignored_links:
            continue

        old_route = old_routes[name]
        new_route = new_routes[name]
        old_route_keys = set(old_route.keys())
        new_route_keys = set(new_route.keys())
        for key in old_route_keys | new_route_keys:
            old_value = old_route.get(key)
            new_value = new_route.get(key)
            if old_value != new_value:
                if new_value is None:
                    def action(routes):
                        del routes[name][key]
                else:
                    def action(routes):
                        routes[name][key] = new_value
                yield ParseResultFix(
                    name, ' - {0}: {1} -> {2}'.format(key, old_value, new_value), action)


def main():
    pages_exceptions = {}
    online_routes = {}
    saved_routes = read_routes()
    fixed_routes = copy.deepcopy(saved_routes)

    with open(os.path.join(exec_root, 'pages_exceptions.txt')) as f:
        for line in f:
            parts = line.strip().split(': ', 2)
            pages_exceptions[parts[2]] = parts[1]
    with open(os.path.join(exec_root, 'pages.txt')) as f:
        for rel_url in f:
            rel_url = rel_url.strip()
            exception = pages_exceptions.get(rel_url)
            if exception == 'ignore':
                continue
            url = u'http://mtb-bg.com' + rel_url.strip()
            content = download_page(url)
            route, warnings = parse_page(url, content, exception == 'include')
            if exception != 'include' and warnings:
                print('On route {0}:'.format(url))
                for warning in warnings:
                    print(' -', warning)
            if route is not None:
                online_routes[route['name']] = route
    last_header = None
    for fix in compare_routes(saved_routes, online_routes, pages_exceptions):
        if fix.route_name != last_header:
            print('On route', fix.route_name)
            last_header = fix.route_name
        if fix.interact_apply(fixed_routes):
            write_routes(fixed_routes)


if __name__ == '__main__':
    main()
