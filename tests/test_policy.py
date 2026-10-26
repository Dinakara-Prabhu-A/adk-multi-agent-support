from types import SimpleNamespace

from support_agent.policy import APPROVAL_QUEUE_KEY, redact_pii, refund_guard

REFUND_TOOL = SimpleNamespace(name="request_refund")


def ctx():
    return SimpleNamespace(state={})


def test_small_refund_passes_through():
    assert refund_guard(REFUND_TOOL, {"order_id": "ORD-1001", "amount": 79.0}, ctx()) is None


def test_large_refund_is_paused_for_human_approval():
    context = ctx()
    result = refund_guard(REFUND_TOOL, {"order_id": "ORD-1002", "amount": 249.0, "reason": "x"}, context)
    assert result["status"] == "pending_human_approval"
    assert context.state[APPROVAL_QUEUE_KEY] == [{"order_id": "ORD-1002", "amount": 249.0, "reason": "x"}]


def test_large_refund_is_queued_once():
    context = ctx()
    args = {"order_id": "ORD-1002", "amount": 249.0}
    refund_guard(REFUND_TOOL, args, context)
    refund_guard(REFUND_TOOL, args, context)
    assert len(context.state[APPROVAL_QUEUE_KEY]) == 1


def test_refund_above_order_total_is_rejected():
    result = refund_guard(REFUND_TOOL, {"order_id": "ORD-1001", "amount": 500.0}, ctx())
    assert result["status"] == "rejected"


def test_refund_for_unknown_order_is_rejected():
    result = refund_guard(REFUND_TOOL, {"order_id": "ORD-0000", "amount": 10.0}, ctx())
    assert result["status"] == "rejected"


def test_other_tools_are_not_affected():
    other = SimpleNamespace(name="get_order_status")
    assert refund_guard(other, {"order_id": "ORD-1001"}, ctx()) is None


def test_redact_pii():
    text = "Card 4111 1111 1111 1111, email asha@example.com, phone +91 9876543210"
    redacted = redact_pii(text)
    assert "4111" not in redacted and "asha@example.com" not in redacted and "9876543210" not in redacted
    assert "[CARD]" in redacted and "[EMAIL]" in redacted and "[PHONE]" in redacted


def test_redact_leaves_order_ids_alone():
    assert redact_pii("Where is ORD-1003?") == "Where is ORD-1003?"
