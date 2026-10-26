from support_agent.tools import (
    check_refund_eligibility,
    escalate_to_human,
    get_order_status,
    request_refund,
    search_policy,
)


class FakeToolContext:
    def __init__(self):
        self.state = {}


def test_order_status_found_and_case_insensitive():
    result = get_order_status("ord-1003")
    assert result["status"] == "found"
    assert result["order_status"] == "in_transit"
    assert result["tracking_number"] == "EK555000111IN"


def test_order_status_not_found():
    assert get_order_status("ORD-9999")["status"] == "not_found"


def test_refund_eligible_within_window():
    result = check_refund_eligibility("ORD-1001")
    assert result["eligible"] is True
    assert result["max_refund"] == 79.0


def test_refund_not_eligible_outside_window():
    result = check_refund_eligibility("ORD-1004")
    assert result["eligible"] is False
    assert "57 days" in result["reason"]


def test_refund_not_eligible_before_delivery():
    assert check_refund_eligibility("ORD-1003")["eligible"] is False


def test_request_refund_records_state():
    ctx = FakeToolContext()
    result = request_refund("ORD-1001", 79.0, "Stopped working", ctx)
    assert result["status"] == "refund_issued"
    assert ctx.state["refunds_issued"][0]["refund_id"] == "RF-1001"


def test_search_policy_finds_refund_timeline():
    results = search_policy("How long do refunds take?")["results"]
    assert results and results[0]["id"] == "refund-timeline"


def test_search_policy_no_match():
    assert search_policy("cricket poem")["results"] == []


def test_escalation_creates_ticket():
    ctx = FakeToolContext()
    assert escalate_to_human("Damaged item", ctx)["ticket_id"] == "ESC-0001"
    assert escalate_to_human("Second issue", ctx)["ticket_id"] == "ESC-0002"
