import os

import requests
from bs4 import BeautifulSoup

from utils import BS4_PARSER

exec_root = os.path.dirname(__file__)


def main():
    index = requests.get('http://mtb-bg.com/index.php/trails/index-routes')
    index.raise_for_status()
    q = BeautifulSoup(index.text, BS4_PARSER)
    found = set()
    with open(os.path.join(exec_root, 'pages.txt'), 'w') as f:
        for link in q.find_all('a'):
            href = link.get('href')
            if not href:
                continue
            if href.startswith('/index.php/trails/gpstracks/'):
                if href not in found:
                    found.add(href)
                    print(href)
                    f.write(href + '\n')
    print('Found {0} links'.format(len(found)))


if __name__ == '__main__':
    main()
