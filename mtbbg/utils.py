from decimal import Decimal


def parse_decimal(s):
    return Decimal(s.replace(',', '.'))
