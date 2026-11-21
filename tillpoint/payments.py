"""Payment provider webhooks. The provider retries a delivery until it gets a 2xx, so events can repeat."""
from . import db


class PaymentError(Exception):
    pass


class Payments:
    def __init__(self, conn):
        self.conn = conn

    def handle_event(self, event, now=None):
        """event: dict(id, type, order_id, amount_cents). Returns the order's status after the event."""
        if event.get("type") != "payment.succeeded":
            return None
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (event["order_id"],)).fetchone()
        if order is None:
            raise PaymentError(f"payment for unknown order {event['order_id']}")
        if order["status"] == "cancelled":
            raise PaymentError(f"order {order['id']} is cancelled")
        # NEW: if the order is already fully paid, a new separate payment is an extra one
        already_paid = self.paid_cents(order["id"]) >= order["total_cents"]
        # INSERT OR IGNORE skips a repeated event_id instead of saving it twice
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO payments (order_id, event_id, amount_cents, received_at, duplicate)"
            " VALUES (?, ?, ?, ?, ?)",
            (order["id"], event["id"], event["amount_cents"],
             db.to_iso(now or db.utcnow()), 1 if already_paid else 0),
        )
        # nothing inserted means a retry; answer normally so the provider stops retrying
        if cur.rowcount == 0:
            return order["status"]
        if order["status"] == "pending" and self.paid_cents(order["id"]) >= order["total_cents"]:
            self.conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order["id"],))
            return "paid"
        return order["status"]

    def paid_cents(self, order_id):
        """Money that counts toward the order. Flagged duplicates are not counted."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS paid FROM payments"
            " WHERE order_id = ? AND duplicate = 0",
            (order_id,),
        ).fetchone()
        return row["paid"]