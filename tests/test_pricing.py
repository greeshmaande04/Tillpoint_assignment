import unittest

from tillpoint import db
from tillpoint.api import App


class CouponTaxTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)
        self.app.catalog.add_product("MUG", "Mug", 1000, stock=10)
        self.conn.execute("INSERT INTO coupons (code, kind, value) VALUES ('TEN', 'percent', 10)")

    def test_tax_is_charged_on_discounted_amount(self):
        order = self.app.orders.create("ana", [("MUG", 2)], region="CA", coupon_code="TEN")
        self.assertEqual(order["discount_cents"], 200)
        self.assertEqual(order["tax_cents"], 131)
        self.assertEqual(order["total_cents"], 1931)