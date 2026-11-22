# NOTES

Fill in every field below before you submit. We read this file first: a submission with an empty field is not graded.
Write in your own words. If you did not fix something, set Status to `not fixed` and say what you found and tried; that still counts.
Status is one of: `fixed`, `partly fixed`, `not fixed`. Commits: the short hashes of the commits for this item, or `none`.

## 1. Report

> Finance says that on some days the revenue in the daily report is higher than what the payment provider paid out, and a few orders show more money received than their total.

**Status:** fixed

**What I saw:** Finance saw revenue higher than the provider's payout, and some orders showed more money received than their total, because the same payment webhook was processed more than once and the same amount was counted again.

**Root cause:** When the same event ID arrived twice, the old handle_event() in payments.py processed it again instead of checking whether it had already been recorded. This increased paid_cents more than once and made the daily sales report show higher revenue than the payment actually received.

**Fix and why:** I used INSERT OR IGNORE in payments.py so a repeated event ID is not saved again, and a repeated event now returns the order's normal status so the provider gets a success reply and stops retrying. I added a unique index on event_id in db.py so the database itself blocks duplicates. This matters because two server workers could process the same event at the same time, and a Python-level check alone cannot reliably stop both from inserting it. I also removed the duplicate payment rows that already existed in the database.

**How I verified it:** The test test_same_webhook_twice_counts_once sends the same webhook twice and checks that the payment is counted only once. The test passes after the fix, and all 14 tests pass.

**Commits:** d6529d0

## 2. Report

> Products show as sold out, or nearly, while the shelf is full. Staff say it gets worse on days when many customers abandon checkout.

**Status:** fixed

**What I saw:** Products showed as sold out, or nearly, while the shelf was full. It got worse on days when many customers abandoned checkout.

**Root cause:** Stock is reserved as soon as an order is created, but cancel() in orders.py only released the stock if the order status was paid. If a customer left checkout while the order was still pending, the order was cancelled but its reserved stock never came back, so it stayed locked.

**Fix and why:** I removed the paid-only condition in cancel() so the stock is released for every order that gets cancelled, pending or paid, because both had stock reserved at creation. Cancelling the same order twice is safe because cancel() returns early if the status is already cancelled, so the release loop is not run a second time.

**How I verified it:** I added test_cancel_pending_order_releases_stock and test_cancelling_twice_does_not_release_stock_twice in tests/test_orders_cancel.py. I ran them against the old orders.py and both failed with 3 != 5. With the fix, all 14 tests pass.

**Commits:** 29bf808

## 3. Report

> Customers in taxed regions who used a coupon say the tax on their receipt is too high. Receipts without a coupon are right.
**Status:** fixed

**What I saw:** Customers in taxed regions who used a coupon were charged too much tax on their receipt. Receipts without a coupon were correct.

**Root cause:** In pricing.py, price_order() calculated the tax on the full subtotal, before the coupon discount was taken off. So with a coupon the customer paid tax on money they were never charged for. Without a coupon there is no discount, so the two amounts are the same and the receipt looked right.

**Fix and why:** In price_order() I now work out the discount first and then call tax_for() on the subtotal minus the discount. That is the amount the customer actually pays for, so it is the correct base for tax. The total is still subtotal minus discount plus tax.

**How I verified it:** I added test_tax_is_charged_on_discounted_amount in tests/test_pricing.py (class CouponTaxTest). It checks the tax on an order with a coupon in a taxed region. The test passes after the fix, and all 14 tests pass.

**Commits:** 9cc5c0d

## 4. Report

> Our shop in India (UTC+5:30) says sales taken in the morning do not appear in that day's report and turn up under the day before.

**Status:** fixed

**What I saw:** The shop in India (UTC+5:30) found that sales taken in the morning did not appear in that day's report and showed up under the day before.

**Root cause:** day_bounds_utc() in reports.py added the UTC offset to the start of the shop's day instead of subtracting it. A zone ahead of UTC starts its day earlier in UTC, so India's midnight is 18:30 UTC on the previous day. The old code started the day at 05:30 UTC, 11 hours too late. A sale at 8:00 AM India time is 02:30 UTC, which fell before that start, so it landed in the previous day's window.

**Fix and why:** In day_bounds_utc() I now subtract utc_offset_minutes from the start of the day. The end is still start plus one day. This gives the true UTC window for a shop-local calendar day, so a morning sale in India is counted on its own day.

**How I verified it:** I added test_india_morning_sale_counts_on_its_own_day in tests/test_reports.py (class DayBoundsTest). It records a payment at 02:30 UTC on 10 March, which is 8:00 AM in India, and checks that daily_sales with offset 330 counts it on 10 March and not on 9 March. It passes after the fix, and all 14 tests pass.

**Commits:** 0fb7baa

## 5. Report

> Ever since we started running two server workers, we have sold more units of an item than we had, and its stock went negative.

**Status:** fixed

**What I saw:** After we started running two server workers, we sold more units of an item than we had, and its stock went negative.

**Root cause:** In catalog.py, reserve() checked the stock using a cached copy of the product, and then reduced the stock in a separate step. Each worker had its own cache, so both could see enough stock, both passed the check, and both took the units. The check and the update were not one atomic step, and the cache could be out of date.

**Fix and why:** I changed reserve() to do a single UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?, and to raise OutOfStock only if no row was changed. The database applies the check and the decrement together, so two workers cannot both take the last units, and a stale cache can no longer cause an oversell. If the product does not exist, it raises UnknownProduct. I also drop the cached copy after the update so it is not used again with the old stock.

**How I verified it:** I added test_two_workers_cannot_oversell in tests/test_stock.py. Two Catalog objects (two workers) both cache the product, the first reserves all 3 units, and the second one's reserve of 3 must raise OutOfStock. It also checks that the stock in the database ends at 0, not negative. It passes after the fix, and all 14 tests pass.

**Commits:** 272055f

## 6. Open question

> Open question from support, no single right answer: sometimes a customer really does pay twice for one order (two separate payments, not a retry of the same one). Today the system records both and says nothing. Decide what should happen, build the smallest version of your decision, and explain what it costs in `NOTES.md`.

**My decision:** Record the second payment but flag it as a duplicate. It does not count as another sale or as revenue.

**Why:** The customer really did pay twice, so the system should not ignore or hide that. But the extra money is not income for the order, so it must stay out of the order's paid total and the daily report. Recording and flagging it lets the team review it and refund it.

**What it costs:** Someone has to review and refund the flagged payments by hand. Nothing alerts the team yet, and nothing refunds the customer automatically. It also adds a duplicate column to the payments table, and any new code that adds up money has to remember to skip rows where duplicate = 1. A payment is flagged only if the order is already fully paid when it arrives, so an overpayment in a single payment is not flagged.

**What I built:** A duplicate column on the payments table in db.py, with an ALTER TABLE for databases that already exist. In payments.py, handle_event() checks if the order is already fully paid when a new payment with a new event ID arrives, and if so saves it with duplicate = 1. A repeat of the same event ID is still ignored as before. paid_cents() in payments.py and daily_sales() in reports.py skip rows where duplicate = 1, so the order total and the daily revenue count the order only once.

**How I verified it:** I added test_second_payment_is_flagged_not_counted in tests/test_payments.py (class DoublePaymentTest). It pays the same order twice with two different event IDs, then checks that paid_cents is still 1200 and that exactly one payment is flagged. I ran it against the old code and it failed with 2400 != 1200, so the second payment was being counted as revenue. With the fix it passes, and all 14 tests pass.

**Commits:** 3c739d8

## Other things I noticed

Problems outside the reports: what, where, and whether you fixed them. Write `none` if there were none.

- Not fixed – Cached price: "get_product()" in catalog.py keeps products in a per-worker cache, and "update_price()" only clears the cache of the worker that made the change. Another worker can keep using the old price, and "create()" in orders.py uses that price to charge the customer.
- Not fixed – Cancel race: "cancel()" reads the order status before starting the transaction, so two workers could both read the same order as pending and release its stock twice.
- Not fixed – Overpayment: A payment larger than the order total is not flagged for review. Only a payment that arrives after the order is already fully paid is flagged.
- Not fixed – No alert: Flagged duplicate payments are stored in the database, but no one is notified and no refund is handled automatically.

## Session logs

Which AI tools you used, and one line per file in `session_logs/`.

I used ChatGPT and Claude as AI assistants.
- session_logs/CHATGPT SESSION 1.pdf: ChatGPT conversation 1, full chat saved as PDF.
- session_logs/CHATGPT SESSION 2.pdf: ChatGPT conversation 2, full chat saved as PDF.
- session_logs/CHATGPT SESSION 3.pdf: ChatGPT conversation 3, full chat saved as PDF.
- session_logs/chatgpt_session.md: the original share links of the ChatGPT chats, kept for reference.
- I also used Claude (mobile app) for report 2 (orders.py cancel()), report 6 (duplicate payment flag in db.py, payments.py, reports.py). I could not export that conversation, so its log is not included.
