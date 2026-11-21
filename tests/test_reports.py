import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App


class DayBoundsTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)
        self.app.catalog.add_product("MUG", "Mug", 1200, stock=10)

    def test_india_morning_sale_counts_on_its_own_day(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        # 08:00 in India (UTC+5:30) on 10 March is 02:30 UTC the same day
        morning = datetime(2025, 3, 10, 2, 30, tzinfo=timezone.utc)
        self.app.payments.handle_event(
            {"id": "evt_in", "type": "payment.succeeded",
             "order_id": order["id"], "amount_cents": 1200}, now=morning)
        today = reports.daily_sales(self.conn, "2025-03-10", utc_offset_minutes=330)
        day_before = reports.daily_sales(self.conn, "2025-03-09", utc_offset_minutes=330)
        self.assertEqual(today["revenue_cents"], 1200)
        self.assertEqual(day_before["revenue_cents"], 0)