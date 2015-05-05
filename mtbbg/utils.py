from __future__ import unicode_literals, print_function
from decimal import Decimal

import simplejson


def read_json(path):
    with open(path, 'r') as f:
        return simplejson.loads(f.read(), use_decimal=True)


def write_json(path, data, dumps_params):
    value = simplejson.dumps(data, **dumps_params)
    with open(path, 'w') as f:
        f.write(value)


def parse_decimal(s):
    return Decimal(s.replace(',', '.'))


class ParseResultFix(object):
    def __init__(self, link, text, action):
        self.link = link
        self.text = text
        self.action = action

    def interact(self):
        print(self.text)
        while True:
            result = raw_input('Apply (y/n): ')
            if result == 'y':
                return True
            elif result == 'n':
                return False

    def apply(self, routes):
        self.action(routes)

    def interact_apply(self, routes):
        if self.interact():
            self.apply(routes)
            return True
        return False
