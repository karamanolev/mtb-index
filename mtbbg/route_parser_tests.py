# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal
import unittest
from bs4 import BeautifulSoup

import route_parser
from utils import BS4_PARSER


class ParserTests(unittest.TestCase):
    def test_plaintext_parser(self):
        self.assertEqual(route_parser.plaintext_parser(None), None)
        self.assertEqual(route_parser.plaintext_parser('тест'), 'тест')

    def test_unnecessary_false_parser(self):
        self.assertEqual(route_parser.unnecessary_false_parser('1-2 литра'), '1-2 литра')
        self.assertEqual(route_parser.unnecessary_false_parser('Не е необходима.'), False)

    def test_length_parser(self):
        self.assertEqual(route_parser.length_parser('км'), None)
        self.assertEqual(route_parser.length_parser('35'), Decimal('35'))
        self.assertEqual(route_parser.length_parser('35 км'), Decimal('35'))
        self.assertEqual(route_parser.length_parser('35.6'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser('35.6 км'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser('35,6 км'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser('35.6км'), Decimal('35.6'))
        self.assertEqual(route_parser.length_parser(
            '43.4 км / 48.3 км с допълнителна обиколка около вр. Свети Илия'), Decimal('43.4'))

    def test_ascent_parser(self):
        self.assertEqual(route_parser.ascent_parser('няма нищо'), None)
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

    def test_terrain_parser(self):
        self.assertEqual(route_parser.terrain_parser('глупав терен'), None)
        self.assertEqual(route_parser.terrain_parser(
            '- асфалт - 13 км - черни пътища -~20 км'),
            [{'terrain': 'асфалт', 'length': Decimal('13')},
             {'terrain': 'черни пътища', 'length': Decimal('20')}]
        )

    def test_water_parser(self):
        self.assertEqual(route_parser.water_parser('не е необходима'), False)
        self.assertEqual(route_parser.water_parser('3'), Decimal('3'))
        self.assertEqual(route_parser.water_parser('3.3'), Decimal('3.3'))
        self.assertEqual(route_parser.water_parser('3,3'), Decimal('3.3'))
        self.assertEqual(route_parser.water_parser('3.3 л'), Decimal('3.3'))
        self.assertEqual(route_parser.water_parser('3.3 л.'), Decimal('3.3'))
        self.assertEqual(route_parser.water_parser('3.3 литра'), Decimal('3.3'))
        self.assertEqual(route_parser.water_parser('3.3 литра.'), Decimal('3.3'))
        self.assertEqual(route_parser.water_parser('3.3 литра., в селото има'),
                         '3.3 литра., в селото има')


class MetaTests(unittest.TestCase):
    def test_split_meta_strings(self):
        self.assertEqual(route_parser.split_meta_strings(
            ['Изходна точка: ', 'здравей', 'свят', 'денивелация : ', '13']),
            {
                'trailhead': 'здравей свят',
                'ascent': '13',
            }
        )

        if __name__ == '__main__':
            unittest.main()

    def test_parse_meta_parts(self):
        parse_results = route_parser.parse_meta_parts({
            'trailhead': 'някаква стойност',
            'ascent': '130 м',
            'terrains': 'глупав терен',
            'random_key': '42',
        })
        self.assertEqual(parse_results[0], {
            'trailhead': 'някаква стойност',
            'ascent': Decimal('130'),
        })
        self.assertEqual(len(parse_results[1]), 2)

    def test_find_metas(self):
        soup = BeautifulSoup(
            '<p><b>Изходна точка: </b>Перперикон <b>Дължина</b> 13km</p>',
            BS4_PARSER,
        )
        self.assertEqual(
            route_parser.find_metas(soup),
            [({'trailhead': 'Перперикон', 'length': Decimal(13)}, [])]
        )

    def test_find_trace_links(self):
        soup = BeautifulSoup(
            '<a href="/test.bin">hello world</a>' +
            '<a href="/test.gpx">точки нарязани до 500 за стари гармини</a>' +
            '<a href="/test.gpx">GPX следа</a>',
            BS4_PARSER,
        )
        self.assertEqual(route_parser.find_trace_links(soup), ['http://mtb-bg.com/test.gpx'])

    def test_parse_empty_page(self):
        with self.assertRaises(Exception):
            route_parser.parse_page('demo', '', False)

    def test_find_name(self):
        soup = BeautifulSoup(
            'blah <a href="balsha-katina" class="contentpagetitle">' +
            'Балша - Кътина</a> blah',
            BS4_PARSER,
        )
        self.assertEqual(route_parser.find_name(soup), 'Балша - Кътина')

    def test_parse_page(self):
        content = (
                '<a class="contentpagetitle"> Заглавие </a>' +
                '<p><b>Изходна точка: </b>Перперикон <b>Дължина</b> 13km</p>' +
                '<a href="/test.bin">hello world</a>' +
                '<a href="/test.gpx">точки нарязани до 500 за стари гармини</a>' +
                '<a href="/test.gpx">GPX следа</a>')
        parse_results = route_parser.parse_page('demo', content, False)
        self.assertEqual(parse_results[0], {
            'name': 'Заглавие',
            'trailhead': 'Перперикон',
            'length': Decimal(13),
            'link': 'demo',
            'traces': ['http://mtb-bg.com/test.gpx']
        })
