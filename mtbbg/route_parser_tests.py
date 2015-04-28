# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal
import unittest

import route_parser


class ParserTests(unittest.TestCase):
    def test_plaintext_parser(self):
        self.assertEqual(route_parser.plaintext_parser(None), None)
        self.assertEqual(route_parser.plaintext_parser('тест'), 'тест')

    def test_length_parser(self):
        self.assertEqual(route_parser.length_parser('км'), None)
        self.assertEqual(route_parser.length_parser('35'), Decimal('35'))
        self.assertEqual(route_parser.length_parser('35 км'), Decimal('35'))
        self.assertEqual(route_parser.length_parser('35.6'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser('35.6 км'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser('35.6км'), Decimal('35.6'))


if __name__ == '__main__':
    unittest.main()
