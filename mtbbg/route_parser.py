# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from collections import defaultdict
from decimal import Decimal
import os
import re

from bs4 import BeautifulSoup
import requests


def plaintext_parser(v):
    return v


def length_parser(v):
    match = re.match('^(?P<length>\d+(\.\d+)?) ?(км)?$', v)
    if match is None:
        return None
    return Decimal(match.group('length'))


keys = {
    'Изходна точка:': 'trailhead',
    'Дължина:': 'length',
    'Денивелация': 'ascent',
    'Продължителност:': 'duration',
    'Вода:': 'water',
    'Храна:': 'food',
    'Терен:': 'terrain',
}
parsers = {
    'trailhead': plaintext_parser,
    'length': length_parser,
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
        if s in keys:
            current_key = keys[s]
        elif current_key:
            parts[current_key].append(s)
    return {k: ' '.join(v) for k, v in parts.items()}


def parse_page(url, content):
    if len(content) == 0:
        raise Exception('Empty HTML file!')
    if url != 'http://mtb-bg.com/index.php/trails/gpstracks/2570-gpstrack0047-volno-baskaltsi':
        pass
        # return
    print('Parsing', url)
    soup = BeautifulSoup(content)
    for p in soup.find_all('p'):
        strings = list(re.sub('[ ]+', ' ', t) for t in p.stripped_strings)
        if 'Изходна точка:' in strings:
            meta_parts = split_meta_strings(strings)
            print(meta_parts)


def main():
    with open(os.path.join(exec_root, 'pages.txt')) as f:
        for rel_url in f:
            url = u'http://mtb-bg.com' + rel_url.strip()
            content = download_page(url)
            parse_page(url, content)


if __name__ == '__main__':
    main()
