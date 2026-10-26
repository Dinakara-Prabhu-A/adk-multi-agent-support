"""In-memory sample data so the project runs without any external system.

In a real deployment these would be calls to an order-management system,
a payments API and a policy knowledge base.
"""

from datetime import date

TODAY = date(2026, 10, 26)

ORDERS: dict[str, dict] = {
    "ORD-1001": {
        "customer": "Asha Rao",
        "item": "Wireless headphones",
        "total": 79.0,
        "status": "delivered",
        "delivered_on": date(2026, 10, 18),
        "carrier": "BlueDart",
        "tracking": "BD123456789IN",
        "refunded": False,
    },
    "ORD-1002": {
        "customer": "Rahul Menon",
        "item": "Smartwatch",
        "total": 249.0,
        "status": "delivered",
        "delivered_on": date(2026, 10, 20),
        "carrier": "Delhivery",
        "tracking": "DL987654321IN",
        "refunded": False,
    },
    "ORD-1003": {
        "customer": "Priya Nair",
        "item": "Laptop stand",
        "total": 45.0,
        "status": "in_transit",
        "delivered_on": None,
        "carrier": "Ekart",
        "tracking": "EK555000111IN",
        "refunded": False,
    },
    "ORD-1004": {
        "customer": "Karthik S",
        "item": "Mechanical keyboard",
        "total": 120.0,
        "status": "delivered",
        "delivered_on": date(2026, 8, 30),
        "carrier": "BlueDart",
        "tracking": "BD000111222IN",
        "refunded": False,
    },
}

POLICIES: list[dict[str, str]] = [
    {
        "id": "returns-window",
        "title": "Return and refund window",
        "text": "Delivered items can be returned for a full refund within 30 days of delivery.",
    },
    {
        "id": "refund-timeline",
        "title": "Refund timeline",
        "text": "Approved refunds reach the original payment method within 5 to 7 business days.",
    },
    {
        "id": "shipping-times",
        "title": "Shipping times",
        "text": "Standard shipping takes 3 to 5 business days. Express shipping takes 1 to 2 business days.",
    },
    {
        "id": "damaged-items",
        "title": "Damaged or wrong items",
        "text": "If an item arrives damaged or wrong, customers get a free replacement or a full refund, "
        "even after 30 days, when reported with a photo.",
    },
    {
        "id": "cancellations",
        "title": "Order cancellations",
        "text": "Orders can be cancelled free of charge until they are shipped.",
    },
]
