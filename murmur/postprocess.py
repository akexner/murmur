import re

FILLER = re.compile(r"(?<!\w)(?:u+m+|u+h+|e+r+m+|äh+m?|ähm+|hmm+|mhm+)(?!\w)[,.]?\s*", re.I)
PARA = re.compile(r"[\s,;:]*(?<!\w)(?:new paragraph|neuer absatz|nächster absatz)(?!\w)[.,!?]?[ \t]*", re.I)
LINE = re.compile(r"[\s,;:]*(?<!\w)(?:new line|newline|neue zeile|nächste zeile)(?!\w)[.,!?]?[ \t]*", re.I)


def _cap_after_breaks(text):
    return re.sub(r"(\n)([a-zäöü])", lambda m: m.group(1) + m.group(2).upper(), text)


def apply(text: str, cfg) -> str:
    if not text:
        return ""
    if cfg["filler_removal"]:
        text = FILLER.sub("", text)
    if cfg["voice_commands"]:
        text = PARA.sub("\n\n", text)
        text = LINE.sub("\n", text)
        text = _cap_after_breaks(text)
    for r in cfg["replacements"]:
        a, b = (r.get("from") or "").strip(), r.get("to", "")
        if a:
            text = re.sub(r"(?<!\w)" + re.escape(a) + r"(?!\w)", lambda m: b, text, flags=re.I)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()
