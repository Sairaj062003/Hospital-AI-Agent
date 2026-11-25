
import re

from src.state.models import AgentState


_INJECTION_PATTERNS = [
    (re.compile(r"ignore (all |the )?previous instructions", re.IGNORECASE), "instruction override attempt"),
    (re.compile(r"disregard (the )?(above|system)", re.IGNORECASE), "instruction override attempt"),
    (re.compile(r"you are now", re.IGNORECASE), "role reassignment attempt"),
    (re.compile(r"act as", re.IGNORECASE), "role reassignment attempt"),
    (re.compile(r"system prompt", re.IGNORECASE), "prompt exfiltration attempt"),
    (re.compile(r"print your instructions", re.IGNORECASE), "prompt exfiltration attempt"),
]



def detect_injection(raw_message: str) -> list[str]:
    injection_types = []
    for pattern, description in _INJECTION_PATTERNS:
        if pattern.search(raw_message):
            injection_types.append(description)
    return injection_types



def run_injection_guard(state: AgentState) -> dict:
    matches = detect_injection(state.raw_message)
    if matches:
        return {"blocked": True, "block_reason": f"Injection patterns detected: {matches}"}
    return {}
   