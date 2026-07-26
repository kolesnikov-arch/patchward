"""Extract the agent's final self-report from a SWE-bench submission trace.

Ten submissions, ten container formats. Each adapter answers one question and nothing
else: *what did the agent say last, in its own voice, about the work it was submitting?*

Written against the five instances named in DEV_SAMPLE.md and frozen before collection.
Standard library only.

Two submissions run several patch attempts and then select one. For those the last
narrative in the file is not necessarily the narrative belonging to the submitted patch,
so their adapters return a SelectionUnclear marker rather than a guess; see
DEV_SAMPLE.md and the pre-registration for how those instances are counted.
"""

import ast
import json
import re

SELECTION_UNCLEAR = "<<SELECTION_UNCLEAR>>"
NO_REPORT = "<<NO_REPORT>>"

# Machinery that can survive unwrapping and is not a statement to anybody.
_MACHINERY = re.compile(r"^(?:<[^>]{1,40}>|finish|submit|done|\W)+$", re.I)


# ---------------------------------------------------------------- normalisation
#
# Three submissions wrap the closing message in machinery. Unwrapping it is a
# scoring decision, not tidying, so it lives here in one place and is named in the
# pre-registration:
#
#   * OpenHands serialises the terminal action as `[finish] [{...'text': '...'}]`.
#     The Python literal is unwrapped; only the text the agent wrote is kept.
#   * Trae and Z.ai wrap deliberation in `<think>...</think>`. Deliberation is not
#     a report to anyone, so it is dropped and only the text outside is scored.
#   * livesweagent prefixes every turn with `THOUGHT:`; the label is dropped, the
#     sentence after it is kept.
#
# If unwrapping leaves only machinery — `<tool_call>finish</tool_call>` and nothing
# else — the instance is marked NO_REPORT rather than scored on the leftovers. That
# happens when an agent's entire closing summary lives inside <think>, i.e. it was
# deliberated and never stated. Whether deliberation counts as a report at all is an
# open question for the pre-registration; both readings are reachable by keeping or
# dropping the <think> rule below, and the study reports the number both ways.


def normalise(text, keep_think=False):
    """`keep_think=True` selects the second reading of §5: deliberation counts as report."""
    if not text:
        return ""
    if text.startswith("[finish]"):
        literal = text[len("[finish]"):].strip()
        try:
            chunks = ast.literal_eval(literal)
            text = "\n".join(
                c.get("text", "") for c in chunks if isinstance(c, dict)
            ) or text
        except (ValueError, SyntaxError):
            pass
    if keep_think:
        text = re.sub(r"</?think>", " ", text)
    else:
        text = re.sub(r"<think>.*?</think>", " ", text, flags=re.S)
    text = re.sub(r"(?m)^\s*THOUGHT:\s*", "", text).strip()
    if not text or _MACHINERY.fullmatch(text):
        return NO_REPORT
    return text


# --------------------------------------------------------------------------- JSON


def _messages(obj):
    """Return the message list from any of the observed JSON shapes."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("messages", "trajectory", "history", "steps", "conversation"):
            value = obj.get(key)
            if isinstance(value, list):
                return value
        # mini-swe-agent nests the run under a single key
        for value in obj.values():
            if isinstance(value, dict):
                nested = _messages(value)
                if nested:
                    return nested
    return None


def _text_of(message):
    """Flatten one message's content, whatever shape it arrived in."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    parts = []
    for chunk in (content if isinstance(content, list) else []) + (
        message.get("blocks") or []
    ):
        if isinstance(chunk, str):
            parts.append(chunk)
        elif isinstance(chunk, dict):
            parts.append(chunk.get("text") or chunk.get("content") or "")
    return "\n".join(p for p in parts if p)


def json_last_assistant(raw):
    """OpenHands, Trae, Sonar, livesweagent — a plain list of role-tagged messages."""
    messages = _messages(json.loads(raw))
    if not messages:
        return ""
    spoken = [
        m for m in messages
        if isinstance(m, dict) and m.get("role") == "assistant" and _text_of(m).strip()
    ]
    if not spoken:
        return ""
    return _text_of(spoken[-1]).strip()


def openhands_events(raw):
    """Z.ai GLM ships the OpenHands event stream rather than a message list.

    Events carry `source` and `action`; the closing statement is the last event the
    agent emitted, normally `action == "finish"`, whose prose sits in `args.thought`.
    """
    history = json.loads(raw).get("history")
    if not isinstance(history, list):
        return ""
    spoken = [
        e for e in history
        if isinstance(e, dict)
        and e.get("source") == "agent"
        and ((e.get("args") or {}).get("thought") or e.get("message"))
    ]
    if not spoken:
        return ""
    finishes = [e for e in spoken if e.get("action") == "finish"]
    last = (finishes or spoken)[-1]
    return ((last.get("args") or {}).get("thought") or last.get("message") or "").strip()


# ---------------------------------------------------------------------------- text


def atlassian(raw):
    """Turns are labelled `AGENT:` / `TOOL CALL (x)` / `TOOL RETURN (x)`."""
    text = _decode(raw)
    turns = list(re.finditer(r"(?m)^AGENT:\s*$", text))
    if not turns:
        return ""
    tail = text[turns[-1].end():]
    return re.split(r"(?m)^TOOL (?:CALL|RETURN)\b", tail)[0].strip()


def anthropic_tools(raw):
    """Prose sits outside the `<function_calls>` / `</function_results>` blocks."""
    text = _decode(raw)
    blocks = list(re.finditer(r"</function_results>", text))
    if not blocks:
        return text[-4000:].strip()
    return text[blocks[-1].end():].strip()


def qodo(raw):
    """A long tool log; the agent's closing narrative follows the last `## Summary`."""
    text = _decode(raw)
    heads = list(re.finditer(r"(?m)^##\s+Summary\s*$", text))
    if heads:
        return text[heads[-1].start():].strip()
    rules = list(re.finditer(r"(?m)^={3,}\s*$", text))
    return (text[rules[-1].end():] if rules else text[-4000:]).strip()


def warp(raw):
    """Several `===== Attempt N =====` blocks, then one selected patch.

    The closing `Output:` summarises the run as a whole ("Analyzed all four patch
    attempts"), so it cannot be attributed to the submitted patch alone.
    """
    text = _decode(raw)
    if len(re.findall(r"=====\s*Attempt\s*\d+\s*=====", text)) > 1:
        return SELECTION_UNCLEAR
    outputs = list(re.finditer(r"(?m)^Output:\s*$", text))
    if not outputs:
        return ""
    tail = text[outputs[-1].end():]
    return re.split(r"={4,}Debug Info Complete={4,}", tail)[0].strip()


def amazon_q(raw):
    """Boxed turns; a trailing `<patch_id>N</patch_id>` names the submitted candidate.

    The narrative boxes are not numbered, so the box belonging to patch N cannot be
    identified from the trace alone whenever more than one candidate was evaluated.
    """
    text = _decode(raw)
    chosen = re.search(r"<patch_id>\s*(\d+)\s*</patch_id>", text)
    boxes = [
        _unbox(segment)
        for segment in re.split(r"╭─ Amazon Q Developer Agent[─╮]*", text)[1:]
    ]
    narratives = [b for b in boxes if b and not re.fullmatch(r"<patch_id>\s*\d+\s*</patch_id>", b)]
    if not narratives:
        return ""
    if chosen and len(narratives) > 1:
        return SELECTION_UNCLEAR
    return narratives[-1]


def _unbox(segment):
    """Strip the box-drawing frame Amazon Q wraps every line in."""
    lines = []
    for line in segment.split("\n"):
        if re.fullmatch(r"[\s│╭╰╮╯─]*", line):
            continue
        lines.append(re.sub(r"^\s*│\s?|\s*│\s*$", "", line).rstrip())
    return "\n".join(lines).strip()


def _decode(raw):
    return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw


# --------------------------------------------------------------------------- table

ADAPTERS = {
    "20251127_openhands_claude-opus-4-5": json_last_assistant,
    "20250928_trae_doubao_seed_code": json_last_assistant,
    "20251205_sonar-foundation-agent_claude-opus-4-5": json_last_assistant,
    "20250930_zai_glm4-6": openhands_events,
    "20251215_livesweagent_claude-opus-4-5": json_last_assistant,
    "20250902_atlassian-rovo-dev": atlassian,
    "20250522_tools_claude-4-opus": anthropic_tools,
    "20250715_qodo_command": qodo,
    "20250901_warp": warp,
    "20250405_amazon-q-developer-agent-20250405-dev": amazon_q,
}


def extract(submission, raw, keep_think=False):
    out = ADAPTERS[submission](raw)
    return out if out == SELECTION_UNCLEAR else normalise(out, keep_think)
