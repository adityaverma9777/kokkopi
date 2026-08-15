"""Engine-agnostic text normalization — conservative pre-pass before TTS.

Ported from VoiceStudio services/text_normalization.py.

Normalizes digits, times, abbreviations, currency, etc. before the text
reaches any TTS engine. Never raises — normalization must not break synthesis.

Pipeline order (load-bearing):
    1. normalize_for_tts()   ← this module
    2. apply_pronunciation() ← pronunciation.py
    3. TTS engine
"""
from __future__ import annotations

import logging
import os
import re
from typing import Callable, Optional

logger = logging.getLogger("kokkopi.text_normalization")

_FULL_NAME_TO_CODE = {
    "english": "en", "german": "de", "spanish": "es", "french": "fr",
    "italian": "it", "portuguese": "pt", "dutch": "nl", "russian": "ru",
    "ukrainian": "uk", "polish": "pl", "turkish": "tr", "czech": "cs",
    "danish": "da", "finnish": "fi", "swedish": "sv", "norwegian": "no",
    "norwegian bokmål": "no", "norwegian nynorsk": "no", "romanian": "ro",
    "hungarian": "hu", "indonesian": "id", "lithuanian": "lt", "latvian": "lv",
    "slovenian": "sl", "serbian": "sr", "hebrew": "he", "persian": "fa",
    "azerbaijani": "az", "vietnamese": "vi", "kazakh": "kz", "standard arabic": "ar",
}
_ISO_ALIASES = {"kk": "kz"}
_NUM2WORDS_LANGS = frozenset({
    "en", "de", "es", "fr", "it", "pt", "nl", "ru", "uk", "pl", "tr", "cs",
    "da", "fi", "sv", "no", "ro", "hu", "id", "lt", "lv", "sl", "sr", "ar",
    "he", "fa", "az", "kz",
})
_DECIMAL_LANGS = frozenset({
    "en", "de", "es", "fr", "it", "pt", "nl", "ru", "uk", "pl", "cs", "da",
    "no", "sv", "fi", "ro", "hu", "id",
})
_PERCENT_WORD = {
    "en": "percent", "de": "Prozent", "es": "por ciento",
    "fr": "pour cent", "it": "per cento", "pt": "por cento", "nl": "procent",
}
_ISO_CODE_RE = re.compile(r"^([a-z]{2,3})(?:[-_]|$)")


def _num2words_lang(language: Optional[str]) -> Optional[str]:
    if not language:
        return None
    s = str(language).strip().lower()
    if not s or s == "auto":
        return None
    code = _FULL_NAME_TO_CODE.get(s)
    if code:
        return code if code in _NUM2WORDS_LANGS else None
    m = _ISO_CODE_RE.match(s)
    if m:
        c = _ISO_ALIASES.get(m.group(1), m.group(1))
        if c in _NUM2WORDS_LANGS:
            return c
    return None


_UNSAFE_CONTROL_CODEPOINTS = frozenset((
    *range(0x00, 0x09), 0x0B, 0x0C, *range(0x0E, 0x20), *range(0x7F, 0xA0),
    *range(0x200B, 0x2010), *range(0x202A, 0x202F), *range(0x2060, 0x2065),
    0xFEFF, 0xFFFD,
))
_UNSAFE_CONTROL_TRANSLATION = dict.fromkeys(_UNSAFE_CONTROL_CODEPOINTS)


def _strip_unsafe_controls(text: str) -> str:
    return text.translate(_UNSAFE_CONTROL_TRANSLATION)


_ENTITIES = {
    "&nbsp;": " ", "&quot;": '"', "&#39;": "'", "&apos;": "'",
    "&hellip;": "…", "&mdash;": "—", "&ndash;": "–",
}
_ENTITY_RE = re.compile("(?:" + "|".join(re.escape(k) for k in _ENTITIES) + "|&amp;(?![a-zA-Z#]))")
_REPEAT_RE = re.compile(r"([!?.,;:~_*#=-])\1{3,}")
_HSPACE_RE = re.compile(r"[^\S\n]+")
_NEWLINE_RE = re.compile(r"\n{3,}")


def _safety_filters(text: str) -> str:
    out = _strip_unsafe_controls(text)
    out = _ENTITY_RE.sub(lambda m: _ENTITIES.get(m.group(0), "&"), out)
    out = _REPEAT_RE.sub(lambda m: m.group(1) * 3, out)
    out = _HSPACE_RE.sub(" ", out)
    out = _NEWLINE_RE.sub("\n\n", out)
    return out.strip()


_BRACKET_SPAN_RE = re.compile(r"\[[^\]\[\n]{0,128}\]")


def _outside_brackets(text: str, fn: Callable[[str], str]) -> str:
    if "[" not in text:
        return fn(text)
    parts: list[str] = []
    last = 0
    for m in _BRACKET_SPAN_RE.finditer(text):
        parts.append(fn(text[last:m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(fn(text[last:]))
    return "".join(parts)


_ABBREVIATIONS: dict[str, list[tuple[str, str, Optional[str]]]] = {
    "en": [
        ("Dr.", "Doctor", "cap"), ("Mr.", "Mister", "cap"), ("Mrs.", "Missus", "cap"),
        ("Prof.", "Professor", "cap"), ("St.", "Saint", "cap"), ("Mt.", "Mount", "cap"),
        ("Jr.", "Junior", None), ("Sr.", "Senior", None), ("vs.", "versus", None),
        ("etc.", "et cetera", None), ("e.g.", "for example", None),
        ("i.e.", "that is", None), ("approx.", "approximately", None),
        ("No.", "number", "digit"),
    ],
    "de": [
        ("Dr.", "Doktor", "cap"), ("Prof.", "Professor", "cap"),
        ("Nr.", "Nummer", "digit"), ("z.B.", "zum Beispiel", None),
        ("z. B.", "zum Beispiel", None), ("d.h.", "das heißt", None),
        ("d. h.", "das heißt", None), ("usw.", "und so weiter", None),
        ("bzw.", "beziehungsweise", None), ("ca.", "circa", None),
    ],
    "es": [
        ("Sr.", "Señor", "cap"), ("Sra.", "Señora", "cap"), ("Srta.", "Señorita", "cap"),
        ("Dr.", "Doctor", "cap"), ("Dra.", "Doctora", "cap"),
        ("Ud.", "usted", None), ("Uds.", "ustedes", None),
        ("etc.", "etcétera", None), ("núm.", "número", "digit"),
    ],
    "fr": [
        ("Mme", "Madame", "cap"), ("Mmes", "Mesdames", "cap"),
        ("Mlle", "Mademoiselle", "cap"), ("Mlles", "Mesdemoiselles", "cap"),
        ("etc.", "et cetera", None), ("n°", "numéro", "digit"), ("N°", "Numéro", "digit"),
    ],
}

_GUARD_LOOKAHEAD = {
    None: "",
    "cap": r"(?=\s+[A-ZÀ-ÖØ-Þ])",
    "digit": r"(?=\s*\d)",
}


def _compile_abbreviations() -> dict[str, tuple[re.Pattern, dict[str, str]]]:
    compiled: dict[str, tuple[re.Pattern, dict[str, str]]] = {}
    for lang, entries in _ABBREVIATIONS.items():
        entries = list(entries)
        for key, expansion, guard in list(entries):
            if key[:1].islower():
                cap_key = key[0].upper() + key[1:]
                if not any(k == cap_key for k, _, _ in entries):
                    entries.append((cap_key, expansion[0].upper() + expansion[1:], guard))
        entries.sort(key=lambda e: len(e[0]), reverse=True)
        lookup = {key: expansion for key, expansion, _ in entries}
        alts = []
        for key, _, guard in entries:
            suffix = r"(?!\w)" if key[-1:].isalnum() else ""
            alts.append(f"{re.escape(key)}{suffix}{_GUARD_LOOKAHEAD[guard]}")
        pattern = re.compile(r"(?<![\\w.])(?:" + "|".join(alts) + ")")
        compiled[lang] = (pattern, lookup)
    return compiled


_ABBREV_COMPILED = _compile_abbreviations()

_TIME_RE = re.compile(r"(?<![\d:.,])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])")
_ORDINAL_RE = re.compile(r"(?<![\w.,])(\d{1,4})(st|nd|rd|th)\b")
_CURRENCY_RE = re.compile(r"(?<!\w)\$(\d{1,6})(?:\.(\d{2}))?(?![\d.,])")
_PERCENT_RE = re.compile(r"(?<![\w.,])(\d{1,6}(?:\.\d{1,4})?)\s?%")
_DECIMAL_RE = re.compile(r"(?<![\w.,:/$%-])(\d{1,6})\.(\d{1,6})(?![\w:/%-])(?![.,]\d)")
_INTEGER_RE = re.compile(r"(?<![\w.,:/$%-])(?!0\d)(\d{1,6})(?![\w:/%-])(?![.,]\d)")
_ORDINAL_SUFFIX = {1: "st", 2: "nd", 3: "rd"}


def _correct_ordinal_suffix(n: int) -> str:
    if 10 <= n % 100 <= 13:
        return "th"
    return _ORDINAL_SUFFIX.get(n % 10, "th")


def _expand_abbreviations(text: str, lang: str) -> str:
    entry = _ABBREV_COMPILED.get(lang)
    if entry is None:
        return text
    pattern, lookup = entry
    return pattern.sub(lambda m: lookup.get(m.group(0), m.group(0)), text)


def _numbers_to_words(text: str, lang: str) -> str:
    try:
        from num2words import num2words
    except ImportError:
        return text

    def _safe(m: re.Match, render: Callable) -> str:
        try:
            return render(m)
        except Exception:
            return m.group(0)

    if lang == "en":
        def _time(m: re.Match) -> str:
            h, mm = int(m.group(1)), int(m.group(2))
            hw = num2words(h, lang="en")
            if mm == 0:
                return f"{hw} o'clock"
            if mm < 10:
                return f"{hw} oh {num2words(mm, lang='en')}"
            return f"{hw} {num2words(mm, lang='en')}"
        text = _TIME_RE.sub(lambda m: _safe(m, _time), text)

        def _ordinal(m: re.Match) -> str:
            n = int(m.group(1))
            if m.group(2) != _correct_ordinal_suffix(n):
                return m.group(0)
            return num2words(n, lang="en", to="ordinal")
        text = _ORDINAL_RE.sub(lambda m: _safe(m, _ordinal), text)

        def _currency(m: re.Match) -> str:
            dollars = int(m.group(1))
            if m.group(2) is not None:
                amount = float(f"{m.group(1)}.{m.group(2)}")
                return num2words(amount, lang="en", to="currency", currency="USD")
            unit = "dollar" if dollars == 1 else "dollars"
            return f"{num2words(dollars, lang='en')} {unit}"
        text = _CURRENCY_RE.sub(lambda m: _safe(m, _currency), text)

    percent_word = _PERCENT_WORD.get(lang)
    if percent_word:
        def _percent(m: re.Match) -> str:
            raw = m.group(1)
            if "." in raw:
                if lang not in _DECIMAL_LANGS:
                    return m.group(0)
                value: object = float(raw)
            else:
                value = int(raw)
            return f"{num2words(value, lang=lang)} {percent_word}"
        text = _PERCENT_RE.sub(lambda m: _safe(m, _percent), text)

    if lang in _DECIMAL_LANGS:
        def _decimal(m: re.Match) -> str:
            return num2words(float(f"{m.group(1)}.{m.group(2)}"), lang=lang)
        text = _DECIMAL_RE.sub(lambda m: _safe(m, _decimal), text)

    def _integer(m: re.Match) -> str:
        raw = m.group(1)
        n = int(raw)
        if len(raw) == 4 and 1500 <= n <= 2099:
            try:
                return num2words(n, lang=lang, to="year")
            except Exception:
                pass
        return num2words(n, lang=lang)

    return _INTEGER_RE.sub(lambda m: _safe(m, _integer), text)


def normalize_text(text: str, language: Optional[str] = None) -> str:
    """Pure, idempotent normalization pass. Never raises."""
    if not text:
        return text or ""
    out = _safety_filters(text)
    lang = _num2words_lang(language)
    if lang:
        if lang in _ABBREV_COMPILED:
            out = _outside_brackets(out, lambda t: _expand_abbreviations(t, lang))
        out = _outside_brackets(out, lambda t: _numbers_to_words(t, lang))
    return out


def normalize_for_tts(text: str, language: Optional[str] = None) -> str:
    """Gated + hardened entry point. Every TTS pipeline calls this once,
    before the pronunciation dictionary, at the text→engine choke point.
    """
    if not text:
        return text or ""
    env = os.environ.get("KOKKOPI_TEXT_NORMALIZATION", "1")
    if env.strip().lower() in ("0", "false", "no", "off"):
        return text
    try:
        return normalize_text(text, language)
    except Exception:
        logger.warning("text normalization failed; using raw text", exc_info=True)
        return text
