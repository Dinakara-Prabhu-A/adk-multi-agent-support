"""Runs the real ADK runtime offline with a scripted model.

The scripted model replays the tool calls a real LLM would make, so these
tests prove the wiring end to end (tools, callbacks, session state) without
an API key.
"""

import asyncio
from collections.abc import AsyncGenerator

from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from support_agent.policy import APPROVAL_QUEUE_KEY, pii_guard, refund_guard
from support_agent.tools import check_refund_eligibility, request_refund


class ScriptedLlm(BaseLlm):
    """Returns pre-written responses in order and records what it was sent."""

    script: list = []
    seen_text: list = []

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        for content in llm_request.contents:
            for part in content.parts or []:
                if part.text:
                    self.seen_text.append(part.text)
        step = self.script.pop(0)
        if isinstance(step, str):
            part = types.Part(text=step)
        else:
            name, args = step
            part = types.Part(function_call=types.FunctionCall(name=name, args=args))
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def run(script: list, message: str) -> tuple[list, dict, ScriptedLlm]:
    model = ScriptedLlm(model="scripted", script=list(script), seen_text=[])
    agent = Agent(
        name="refunds_agent",
        model=model,
        instruction="Handle refunds.",
        tools=[check_refund_eligibility, request_refund],
        before_tool_callback=refund_guard,
        before_model_callback=pii_guard,
    )

    async def _go():
        sessions = InMemorySessionService()
        runner = Runner(app_name="test", agent=agent, session_service=sessions)
        session = await sessions.create_session(app_name="test", user_id="u1")
        responses = []
        async for event in runner.run_async(
            user_id="u1",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=message)]),
        ):
            for part in (event.content.parts if event.content else None) or []:
                if part.function_response:
                    responses.append((part.function_response.name, dict(part.function_response.response)))
        final = await sessions.get_session(app_name="test", user_id="u1", session_id=session.id)
        return responses, dict(final.state), model

    return asyncio.run(_go())


def test_small_refund_is_issued():
    responses, state, _ = run(
        [
            ("check_refund_eligibility", {"order_id": "ORD-1001"}),
            ("request_refund", {"order_id": "ORD-1001", "amount": 79.0, "reason": "Broken"}),
            "Your refund has been issued.",
        ],
        "Refund ORD-1001 please",
    )
    name, result = responses[-1]
    assert name == "request_refund"
    assert result["status"] == "refund_issued"
    assert state["refunds_issued"][0]["order_id"] == "ORD-1001"


def test_large_refund_is_blocked_and_queued_for_a_human():
    responses, state, _ = run(
        [
            ("check_refund_eligibility", {"order_id": "ORD-1002"}),
            ("request_refund", {"order_id": "ORD-1002", "amount": 249.0, "reason": "Changed mind"}),
            "A support lead needs to approve this refund.",
        ],
        "Refund ORD-1002 please",
    )
    name, result = responses[-1]
    assert name == "request_refund"
    assert result["status"] == "pending_human_approval"
    assert "refunds_issued" not in state  # the tool itself never ran
    assert state[APPROVAL_QUEUE_KEY][0]["order_id"] == "ORD-1002"


def test_pii_never_reaches_the_model():
    _, _, model = run(["Thanks, how can I help?"], "My card is 4111 1111 1111 1111, email asha@example.com")
    sent = " ".join(model.seen_text)
    assert "4111" not in sent and "asha@example.com" not in sent
    assert "[CARD]" in sent and "[EMAIL]" in sent
