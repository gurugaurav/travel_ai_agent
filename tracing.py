"""Arize AX tracing setup for TravelGPT.

Must be imported BEFORE any LangChain/LangGraph imports so the
OpenTelemetry instrumentation hooks are registered first.
"""

import os
from arize.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

_initialized = False


def init_tracing(project_name: str = "travelgpt") -> None:
    global _initialized
    if _initialized:
        return

    space_id = os.environ.get("ARIZE_SPACE_ID")
    api_key = os.environ.get("ARIZE_API_KEY")

    if not space_id or not api_key:
        print("[tracing] ARIZE_SPACE_ID or ARIZE_API_KEY not set — skipping Arize tracing.")
        return

    tracer_provider = register(
        space_id=space_id,
        api_key=api_key,
        project_name=project_name,
    )

    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    _initialized = True
    print(f"[tracing] Arize AX tracing enabled → project='{project_name}'")
