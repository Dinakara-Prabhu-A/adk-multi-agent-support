"""Runs the ADK evaluation suite against a real Gemini model.

Skipped unless GOOGLE_API_KEY is set. In CI it runs only from the manual
"Live eval" workflow, so pull requests never spend API credits.
"""

import os
from pathlib import Path

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

EVAL_DIR = Path(__file__).parent.parent / "eval"


@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="needs GOOGLE_API_KEY")
@pytest.mark.asyncio
async def test_core_support_flows():
    await AgentEvaluator.evaluate(
        agent_module="support_agent",
        eval_dataset_file_path_or_dir=str(EVAL_DIR / "support.evalset.json"),
        num_runs=2,
    )
