"""Tools the agents can call. Each returns a plain dict the model can read."""

import re

from google.adk.tools import ToolContext

from .data import ORDERS, POLICIES, TODAY

RETURN_WINDOW_DAYS = 30


def _find_order(order_id: str) -> dict | None:
    return ORDERS.get(order_id.strip().upper())


def get_order_status(order_id: str) -> dict:
    """Look up the current status and tracking details of an order.

    Args:
        order_id: The order ID, for example ORD-1001.
    """
    order = _find_order(order_id)
    if order is None:
        return {"status": "not_found", "order_id": order_id}
    return {
        "status": "found",
        "order_id": order_id.upper(),
        "item": order["item"],
        "order_status": order["status"],
        "carrier": order["carrier"],
        "tracking_number": order["tracking"],
        "delivered_on": order["delivered_on"].isoformat() if order["delivered_on"] else None,
    }


def check_refund_eligibility(order_id: str) -> dict:
    """Check whether an order can be refunded under the 30-day return policy.

    Args:
        order_id: The order ID, for example ORD-1001.
    """
    order = _find_order(order_id)
    if order is None:
        return {"eligible": False, "reason": "Order not found."}
    if order["refunded"]:
        return {"eligible": False, "reason": "This order has already been refunded."}
    if order["status"] != "delivered":
        return {"eligible": False, "reason": "The order has not been delivered yet."}
    days = (TODAY - order["delivered_on"]).days
    if days > RETURN_WINDOW_DAYS:
        return {
            "eligible": False,
            "reason": f"Delivered {days} days ago, outside the {RETURN_WINDOW_DAYS}-day return window.",
        }
    return {"eligible": True, "max_refund": order["total"], "days_since_delivery": days}


def request_refund(order_id: str, amount: float, reason: str, tool_context: ToolContext) -> dict:
    """Issue a refund for an eligible order.

    Large refunds are paused for human approval by a guardrail before this runs.

    Args:
        order_id: The order ID, for example ORD-1001.
        amount: Refund amount in the order's currency.
        reason: Short reason given by the customer.
    """
    order = _find_order(order_id)
    if order is None:
        return {"status": "rejected", "reason": "Order not found."}
    refund_id = f"RF-{order_id.upper().split('-')[-1]}"
    issued = list(tool_context.state.get("refunds_issued", []))
    issued.append({"refund_id": refund_id, "order_id": order_id.upper(), "amount": amount, "reason": reason})
    tool_context.state["refunds_issued"] = issued
    return {
        "status": "refund_issued",
        "refund_id": refund_id,
        "amount": amount,
        "eta": "5 to 7 business days",
    }


def search_policy(query: str) -> dict:
    """Search the store's policy knowledge base.

    Args:
        query: The customer's question in plain words.
    """
    words = set(re.findall(r"[a-z]+", query.lower())) - {"the", "a", "an", "is", "my", "i", "can", "do", "how", "what"}
    scored = []
    for policy in POLICIES:
        text = f"{policy['title']} {policy['text']}".lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, policy))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [{"id": p["id"], "title": p["title"], "text": p["text"]} for _, p in scored[:2]]
    return {"results": results} if results else {"results": [], "note": "No matching policy found."}


def escalate_to_human(summary: str, tool_context: ToolContext) -> dict:
    """Hand the conversation to a human support agent.

    Args:
        summary: One or two sentences describing the customer's issue.
    """
    tickets = list(tool_context.state.get("escalations", []))
    ticket_id = f"ESC-{len(tickets) + 1:04d}"
    tickets.append({"ticket_id": ticket_id, "summary": summary})
    tool_context.state["escalations"] = tickets
    return {"status": "escalated", "ticket_id": ticket_id}
