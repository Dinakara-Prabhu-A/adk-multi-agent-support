import json
from pathlib import Path

from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_set import EvalSet

from support_agent.agent import root_agent
from support_agent.policy import refund_guard

EVAL_DIR = Path(__file__).parent.parent / "eval"


def test_coordinator_routes_to_three_specialists():
    assert root_agent.name == "support_coordinator"
    assert [a.name for a in root_agent.sub_agents] == ["order_status_agent", "refunds_agent", "policy_agent"]


def test_refund_guardrail_is_attached():
    refunds = next(a for a in root_agent.sub_agents if a.name == "refunds_agent")
    assert refunds.before_tool_callback is refund_guard


def test_every_agent_redacts_pii():
    for agent in [root_agent, *root_agent.sub_agents]:
        assert agent.before_model_callback is not None, agent.name


def test_evalset_is_valid_and_matches_agents():
    eval_set = EvalSet.model_validate_json((EVAL_DIR / "support.evalset.json").read_text())
    assert len(eval_set.eval_cases) >= 6
    agent_names = {a.name for a in root_agent.sub_agents}
    for case in eval_set.eval_cases:
        for call in case.conversation[0].intermediate_data.tool_uses:
            if call.name == "transfer_to_agent":
                assert call.args["agent_name"] in agent_names, case.eval_id


def test_eval_config_is_valid():
    EvalConfig.model_validate(json.loads((EVAL_DIR / "test_config.json").read_text()))
