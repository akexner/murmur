import re

FILLER = re.compile(r"(?<!\w)(?:u+m+|u+h+|e+r+m+|äh+m?|ähm+|hmm+|mhm+)(?!\w)[,.]?\s*", re.I)
PARA = re.compile(r"[\s,;:]*(?<!\w)(?:new paragraph|neuer absatz|nächster absatz)(?!\w)[.,!?]?[ \t]*", re.I)
LINE = re.compile(r"[\s,;:]*(?<!\w)(?:new line|newline|neue zeile|nächste zeile)(?!\w)[.,!?]?[ \t]*", re.I)


def _cap_after_breaks(text):
    return re.sub(r"(\n)([a-zäöü])", lambda m: m.group(1) + m.group(2).upper(), text)


UNDO_PHRASES = {"scratch that", "undo that", "delete that", "undo last", "undo", "streich das", "streiche das",
                "das streichen", "lösch das", "lösche das", "das löschen", "rückgängig", "mach das rückgängig"}
SNIPPET_PREFIX = r"(?:insert|snippet|text ?baustein|baustein|füge ein|einfügen)"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()


def is_undo(text: str) -> bool:
    return _norm(text) in UNDO_PHRASES


def fix_case(text: str, terms) -> str:
    """Write known terms the way they should be spelled (datev -> DATEV, umsatzsteuer -> Umsatzsteuer)."""
    for t in sorted({t.strip() for t in terms if t and t.strip()}, key=len, reverse=True):
        pat = r"\s+".join(re.escape(w) for w in t.split())
        text = re.sub(r"(?<!\w)" + pat + r"(?!\w)", lambda m, t=t: t, text, flags=re.I)
    return text


def expand_snippets(text: str, snippets):
    """'closing email' (or 'insert closing email') -> the saved block. Returns (text, used)."""
    used = False
    for sn in snippets or []:
        trig, body = (sn.get("trigger") or "").strip(), sn.get("text") or ""
        if not trig or not body:
            continue
        whole = _norm(text)
        t = _norm(trig)
        if whole == t or re.fullmatch(SNIPPET_PREFIX + r" " + re.escape(t), whole):
            return body, True
        pat = r"(?<!\w)" + SNIPPET_PREFIX + r"\s+" + r"\W*".join(re.escape(w) for w in trig.split()) + r"[.,!?]?"
        new = re.sub(pat, lambda m, b=body: b, text, flags=re.I)
        if new != text:
            text, used = new, True
    return text, used


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
