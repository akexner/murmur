"""Optional text polishing with a LOCAL Ollama model. Never talks to anything but 127.0.0.1.

Safe by design: any error, timeout or suspicious result falls back to the original text,
so dictation can never be lost or mangled by this step.
"""
import json
import logging
import re
import urllib.request

log = logging.getLogger("murmur")
BASE = "http://127.0.0.1:11434"      # fixed on purpose: local only, not configurable

PROMPT = (
    "You clean up dictated text. Fix punctuation and capitalization, remove filler words and "
    "false starts. Keep the same language as the input (German stays German, English stays English). "
    "Keep every line break exactly as it is. Do NOT add, remove or change facts, names or numbers, "
    "do not translate, do not answer questions in the text. Output ONLY the cleaned text, "
    "nothing else.\n\nText:\n"
)


def _call(path, payload=None, timeout=5):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def models():
    """Names of locally installed Ollama models, or [] if Ollama isn't running."""
    try:
        return sorted(m["name"] for m in _call("/api/tags").get("models", [])
                      if ":cloud" not in m["name"] and not m["name"].endswith("-cloud"))
    except Exception:
        return []


STYLES = {
    "formal": "Tone: polite, professional and formal (suitable for an email to a client or an authority). ",
    "friendly": "Tone: warm, friendly and natural, but still correct. ",
    "concise": "Tone: short and to the point; remove padding but keep every fact. ",
}


def polish(text: str, model: str, timeout=45, style: str = "") -> str:
    """Polish each line separately so the line breaks you dictated are always preserved."""
    if not text.strip() or not model:
        return text
    if "\n" in text:
        parts = re.split(r"(\n+)", text)
        return "".join(p if (not p.strip() or p.startswith("\n")) else _polish_one(p, model, timeout, style)
                       for p in parts)
    return _polish_one(text, model, timeout, style)


def _polish_one(text: str, model: str, timeout, style: str = "") -> str:
    try:
        prompt = PROMPT.replace("Text:\n", STYLES.get(style, "") + "\n\nText:\n") + text
        out = _call("/api/generate", {"model": model, "prompt": prompt, "stream": False,
                                      "think": False,
                                      "options": {"temperature": 0, "num_predict": max(256, len(text) * 2)}},
                    timeout=timeout).get("response", "")
        out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()
    except Exception as e:
        log.warning("ollama cleanup skipped: %s", e)
        return text
    # Reject empty or wildly different output (hallucination guard).
    if not out or len(out) > len(text) * 1.6 + 20 or len(out) < len(text) * 0.4:
        log.warning("ollama cleanup rejected (length %s -> %s)", len(text), len(out))
        return text
    if not faithful(text, out):
        log.warning("ollama cleanup rejected (a long word or a number was changed)")
        return text
    return out


def _squash(s: str) -> str:
    return re.sub(r"[^0-9a-zäöüß]", "", s.lower())


def faithful(original: str, polished: str) -> bool:
    """True only if every long word (names, compound tax terms) and every number of the original is still
    present in the polished text. Small local models sometimes 'correct' Umsatzsteuervoranmeldung into
    Umsatzsteuererklärung or change 4711 into 4712; in that case we prefer the original text."""
    out = _squash(polished)
    for w in re.findall(r"[A-Za-zÄÖÜäöüß-]{10,}", original):
        if _squash(w) not in out:
            return False
    return all(d in out for d in re.findall(r"\d+", original))
