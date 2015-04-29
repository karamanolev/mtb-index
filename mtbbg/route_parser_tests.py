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
        self.assertEqual(route_parser.length_parser('35,6 км'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser('35.6км'), Decimal('35.6'))

    def test_ascent_parser(self):
        self.assertEqual(route_parser.ascent_parser('840'), Decimal('840'))
        self.assertEqual(route_parser.ascent_parser('840м'), Decimal('840'))
        self.assertEqual(route_parser.ascent_parser('840m'), Decimal('840'))
        self.assertEqual(route_parser.ascent_parser('840 м'), Decimal('840'))
        self.assertEqual(route_parser.ascent_parser('840 m'), Decimal('840'))
        self.assertEqual(route_parser.ascent_parser('(изкачване): 840 m'), Decimal('840'))
        self.assertEqual(route_parser.ascent_parser('(спускане): 840 m'), Decimal('-840'))

    def test_difficulty_parser(self):
        self.assertEqual(route_parser.difficulty_parser('T5 R1 някакъв рандом текст'),
                         ['R1', 'T5'])
        self.assertEqual(route_parser.difficulty_parser('високо (R1, R2, Т3, Т4, Т5, F, X)'),
                         ['R1', 'R2', 'T3', 'T4', 'T5', 'F', 'X'])

    def test_strenuousness_parser(self):
        self.assertEqual(route_parser.strenuousness_parser('бла бла'), None)
        self.assertEqual(route_parser.strenuousness_parser('КФН='), None)
        self.assertEqual(route_parser.strenuousness_parser('КФН=1'), 1)
        self.assertEqual(route_parser.strenuousness_parser('КФН=13'), 13)
        self.assertEqual(route_parser.strenuousness_parser('Средно КФН=6'), 6)


if __name__ == '__main__':
    unittest.main()
