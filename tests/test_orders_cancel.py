import unittest

from tillpoint import db
from tillpoint.catalog import Catalog
from tillpoint.orders import Orders


class CancelOrderStockTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.catalog = Catalog(self.conn)
        self.orders = Orders(self.conn, self.catalog)
        self.catalog.add_product("TEE", "T-shirt", 2500, stock=5)

    def stock(self):
        # read straight from the db, so a stale cache cannot fool the test
        return self.conn.execute(
            "SELECT stock FROM products WHERE sku = 'TEE'"
        ).fetchone()["stock"]

    def test_cancel_pending_order_releases_stock(self):
        order = self.orders.create("alice", [("TEE", 2)])
        self.assertEqual(order["status"], "pending")
        self.assertEqual(self.stock(), 3)

        self.orders.cancel(order["id"])

        self.assertEqual(self.stock(), 5)

    def test_cancelling_twice_does_not_release_stock_twice(self):
        order = self.orders.create("alice", [("TEE", 2)])
        self.orders.cancel(order["id"])
        self.orders.cancel(order["id"])

        self.assertEqual(self.stock(), 5)


if __name__ == "__main__":
    unittest.main()