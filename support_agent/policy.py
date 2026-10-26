"""Guardrails that run outside the LLM.

The model decides *what* to do; these callbacks decide what it is *allowed*
to do. Keeping them in plain Python makes them deterministic and testable.
"""

import re
from typing import Any

from .data import ORDERS

# Refunds up to this amount are automatic. Anything larger waits for a human.
REFUND_AUTO_APPROVE_LIMIT = 100.0

APPROVAL_QUEUE_KEY = "approval_queue"

_PII_PATTERNS = [
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[CARD]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?\d{10}(?!\d)"), "[PHONE]"),
]


def redact_pii(text: str) -> str:
    """Mask card numbers, emails and phone numbers before text reaches the model."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def pii_guard(callback_context: Any, llm_request: Any) -> None:
    """before_model_callback: redact PII in every text part sent to the model."""
    for content in llm_request.contents or []:
        for part in content.parts or []:
            if getattr(part, "text", None):
                part.text = redact_pii(part.text)
    return None


def refund_guard(tool: Any, args: dict[str, Any], tool_context: Any) -> dict | None:
    """before_tool_callback: enforce refund rules before the tool runs.

    Returning a dict skips the tool and hands that dict back to the model as
    the tool result. Returning None lets the call go ahead.
    """
    if tool.name != "request_refund":
        return None

    order_id = str(args.get("order_id", "")).upper()
    amount = float(args.get("amount", 0))
    order = ORDERS.get(order_id)

    if order is None:
        return {"status": "rejected", "reason": f"Order {order_id} does not exist."}
    if amount <= 0 or amount > order["total"]:
        return {
            "status": "rejected",
            "reason": f"Refund amount must be between 0 and the order total ({order['total']}).",
        }

    if amount > REFUND_AUTO_APPROVE_LIMIT:
        queue = list(tool_context.state.get(APPROVAL_QUEUE_KEY, []))
        if not any(item["order_id"] == order_id for item in queue):
            queue.append({"order_id": order_id, "amount": amount, "reason": args.get("reason", "")})
            tool_context.state[APPROVAL_QUEUE_KEY] = queue
        return {
            "status": "pending_human_approval",
            "order_id": order_id,
            "amount": amount,
            "message": (
                f"Refunds above {REFUND_AUTO_APPROVE_LIMIT:.0f} need approval from a support lead. "
                "The request is queued and the customer will be updated within 24 hours."
            ),
        }
    return None
