"""Builds eval/support.evalset.json from readable Python cases.

Keeping the cases in code makes them easy to review and extend; the JSON is
what `adk eval` reads. Run: python eval/build_evalset.py
"""

import json
from pathlib import Path

from google.adk.evaluation.eval_case import EvalCase, IntermediateData, Invocation
from google.adk.evaluation.eval_set import EvalSet
from google.genai import types

OUT = Path(__file__).parent / "support.evalset.json"

# (eval_id, user message, expected tool calls in order, reference answer)
CASES = [
    (
        "track_order_in_transit",
        "Where is my order ORD-1003?",
        [
            ("transfer_to_agent", {"agent_name": "order_status_agent"}),
            ("get_order_status", {"order_id": "ORD-1003"}),
        ],
        "Your order ORD-1003, the laptop stand, is in transit with Ekart. Tracking number: EK555000111IN.",
    ),
    (
        "refund_small_auto_approved",
        "My headphones from order ORD-1001 stopped working, I want a refund.",
        [
            ("transfer_to_agent", {"agent_name": "refunds_agent"}),
            ("check_refund_eligibility", {"order_id": "ORD-1001"}),
            ("request_refund", {"order_id": "ORD-1001", "amount": 79.0, "reason": "Headphones stopped working"}),
        ],
        "Your refund of 79 for order ORD-1001 has been issued (refund ID RF-1001). "
        "It will reach your original payment method in 5 to 7 business days.",
    ),
    (
        "refund_large_needs_human_approval",
        "Please refund order ORD-1002, I changed my mind about the smartwatch.",
        [
            ("transfer_to_agent", {"agent_name": "refunds_agent"}),
            ("check_refund_eligibility", {"order_id": "ORD-1002"}),
            ("request_refund", {"order_id": "ORD-1002", "amount": 249.0, "reason": "Changed mind"}),
        ],
        "Your refund request of 249 for order ORD-1002 needs approval from a support lead because it is "
        "above 100. It has been queued and you will get an update within 24 hours.",
    ),
    (
        "refund_outside_return_window",
        "I want to return my keyboard, order ORD-1004.",
        [
            ("transfer_to_agent", {"agent_name": "refunds_agent"}),
            ("check_refund_eligibility", {"order_id": "ORD-1004"}),
        ],
        "Order ORD-1004 was delivered 57 days ago, outside the 30-day return window, so it can't be "
        "refunded. I can escalate it to a human agent if you'd like.",
    ),
    (
        "policy_refund_timeline",
        "How long do refunds take to reach my account?",
        [
            ("transfer_to_agent", {"agent_name": "policy_agent"}),
            ("search_policy", {"query": "refund timeline"}),
        ],
        "Approved refunds reach your original payment method within 5 to 7 business days.",
    ),
    (
        "out_of_scope_request",
        "Can you write me a poem about cricket?",
        [],
        "Sorry, I can only help with orders, refunds and store policies.",
    ),
]


def build() -> EvalSet:
    cases = []
    for eval_id, user_text, tool_calls, reference in CASES:
        invocation = Invocation(
            invocation_id=f"{eval_id}-1",
            user_content=types.Content(role="user", parts=[types.Part(text=user_text)]),
            final_response=types.Content(role="model", parts=[types.Part(text=reference)]),
            intermediate_data=IntermediateData(
                tool_uses=[types.FunctionCall(name=name, args=args) for name, args in tool_calls]
            ),
        )
        cases.append(EvalCase(eval_id=eval_id, conversation=[invocation]))
    return EvalSet(
        eval_set_id="support_agent_core",
        name="Core support flows",
        description="Routing, tool use, the human-approval guardrail and refusals.",
        eval_cases=cases,
    )


if __name__ == "__main__":
    data = build().model_dump(mode="json", by_alias=True, exclude_none=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {len(data['eval_cases'])} cases to {OUT}")
