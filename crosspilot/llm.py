"""Single tool-use loop shared by every agent (design §7.1)."""
import functools
import json
import os

from crosspilot import fakes

MODEL = os.environ.get("CROSSPILOT_MODEL", "claude-sonnet-5-5")
MAX_TURNS = 5

AGENT_NAMES = {
    "cross_sell": "Venta cruzada",
    "risk": "Riesgo",
    "brief": "Visita",
    "chat_cross_sell": "Venta cruzada",
    "chat_risk": "Riesgo",
}


class AgentError(Exception):
    def __init__(self, agent):
        self.agent = agent
        super().__init__(f"{AGENT_NAMES.get(agent, agent)} no respondió")


@functools.cache
def _client():
    import anthropic

    return anthropic.Anthropic(timeout=60)


def run_agent(agent, system, user, tools, submit_tool, handlers=None, fake=False, fake_ctx=None):
    """Loop until the model calls `submit_tool`; returns that tool's input."""
    if fake:
        return fakes.respond(agent, fake_ctx or {})
    import anthropic

    handlers = handlers or {}
    messages = [{"role": "user", "content": user}]
    try:
        for _ in range(MAX_TURNS):
            resp = _client().messages.create(
                model=MODEL, max_tokens=1500, system=system, tools=tools,
                tool_choice={"type": "any"}, messages=messages)
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                if block.name == submit_tool:
                    return block.input
                handler = handlers.get(block.name)
                out = handler(**block.input) if handler else {"error": f"herramienta desconocida: {block.name}"}
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(out, ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
    except (anthropic.AnthropicError, TypeError) as exc:
        # TypeError: the model sent tool arguments the handler does not accept.
        raise AgentError(agent) from exc
    raise AgentError(agent)
