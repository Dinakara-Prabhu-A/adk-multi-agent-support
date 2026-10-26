"""Multi-agent customer support system built with Google ADK.

A coordinator routes each request to one specialist agent. Guardrails run as
callbacks, so the rules hold no matter what the model decides.
"""

import os

from google.adk.agents import Agent

from .policy import pii_guard, refund_guard
from .tools import (
    check_refund_eligibility,
    escalate_to_human,
    get_order_status,
    request_refund,
    search_policy,
)

MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")

order_status_agent = Agent(
    name="order_status_agent",
    model=MODEL,
    description="Answers questions about where an order is, its delivery status and tracking.",
    instruction=(
        "You help customers track orders. Always call get_order_status with the order ID before "
        "answering. If the customer gave no order ID, ask for it. Reply in two or three short "
        "sentences with the status, carrier and tracking number."
    ),
    tools=[get_order_status],
    before_model_callback=pii_guard,
)

refunds_agent = Agent(
    name="refunds_agent",
    model=MODEL,
    description="Handles refund and return requests for orders.",
    instruction=(
        "You handle refunds. Steps: 1) call check_refund_eligibility. 2) If eligible, call "
        "request_refund with the full order amount unless the customer asked for less, and a short "
        "reason. 3) Tell the customer the outcome plainly. If the result is pending_human_approval, "
        "explain that a support lead must approve it and give the 24-hour timeline. Never promise a "
        "refund the tools did not confirm. If not eligible, explain why and offer escalate_to_human."
    ),
    tools=[check_refund_eligibility, request_refund, escalate_to_human],
    before_tool_callback=refund_guard,
    before_model_callback=pii_guard,
)

policy_agent = Agent(
    name="policy_agent",
    model=MODEL,
    description="Answers general questions about store policies: returns, shipping, cancellations, damaged items.",
    instruction=(
        "Answer policy questions using only search_policy results. Quote the relevant rule in plain "
        "words. If nothing matches, say you are not sure and offer to escalate_to_human."
    ),
    tools=[search_policy, escalate_to_human],
    before_model_callback=pii_guard,
)

root_agent = Agent(
    name="support_coordinator",
    model=MODEL,
    description="Front-line coordinator for customer support.",
    instruction=(
        "You are the first point of contact for an online store's customer support. Work out what "
        "the customer needs and transfer to exactly one specialist: order_status_agent for "
        "tracking and delivery, refunds_agent for refunds and returns, policy_agent for general "
        "policy questions. For anything unrelated to the store, politely say you can only help "
        "with orders, refunds and store policies. Do not answer specialist questions yourself."
    ),
    sub_agents=[order_status_agent, refunds_agent, policy_agent],
    before_model_callback=pii_guard,
)
