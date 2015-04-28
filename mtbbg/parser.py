# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os

from bs4 import BeautifulSoup
import requests

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


def parse_page(url, content):
    if url != 'http://mtb-bg.com/index.php/trails/gpstracks/2613-gpstrack-2014-gorna-breznitsa-3':
        pass
        # return
    print('Parsing', url)
    soup = BeautifulSoup(content)
    for p in soup.find_all('p'):
        t = p.text
        if 'Изходна' in t:
            print('; '.join(p.stripped_strings))


def main():
    with open(os.path.join(exec_root, 'pages.txt')) as f:
        for rel_url in f:
            url = u'http://mtb-bg.com' + rel_url.strip()
            content = download_page(url)
            parse_page(url, content)


if __name__ == '__main__':
    main()
