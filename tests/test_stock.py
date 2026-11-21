import unittest

from tillpoint import db
from tillpoint.catalog import Catalog, OutOfStock


class TwoWorkersStockTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.worker_a = Catalog(self.conn)
        self.worker_b = Catalog(self.conn)
        self.worker_a.add_product("TEE", "T-shirt", 2500, stock=3)

    def test_two_workers_cannot_oversell(self):
        # both workers have looked at the product, so both have it cached
        self.worker_a.get_product("TEE")
        self.worker_b.get_product("TEE")
        self.worker_a.reserve("TEE", 3)
        with self.assertRaises(OutOfStock):
            self.worker_b.reserve("TEE", 3)
        stock = self.conn.execute("SELECT stock FROM products WHERE sku = 'TEE'").fetchone()["stock"]
        self.assertEqual(stock, 0)