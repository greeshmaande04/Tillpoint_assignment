import unittest

from tillpoint import db
from tillpoint.api import App


class DuplicateWebhookTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)
        self.app.catalog.add_product("MUG", "Mug", 1200, stock=10)

    def test_same_webhook_twice_counts_once(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        event = {"id": "evt_dup", "type": "payment.succeeded",
                 "order_id": order["id"], "amount_cents": 1200}
        self.app.payments.handle_event(event)
        self.app.payments.handle_event(event)
        self.assertEqual(self.app.payments.paid_cents(order["id"]), 1200)
