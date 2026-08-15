"""Sentence chunker for streaming TTS.

Adapted from Patter (https://github.com/PatterAI/Patter), MIT License,
Copyright (c) 2026 Patter Contributors. Ported behaviour-identical.

Accumulates streaming text (LLM tokens or a whole request) and yields
complete sentences. Regex-based marker replacement handles abbreviations,
acronyms, decimals, websites, ellipsis, and CJK/non-Latin punctuation.
Used by the voice pipeline to synthesize sentence-by-sentence for low
time-to-first-audio.
"""
from __future__ import annotations

import re

DEFAULT_MIN_SENTENCE_LEN = 20
DEFAULT_MIN_WORDS_FOR_SHORT_FLUSH = 1

HONORIFICS_EN = ("Mr","St","Mrs","Ms","Dr","Prof","Gen","Sen","Rep","Lt","Cpt","Capt","Col","Cmdr","Adm")
HONORIFICS_IT = ("Sig","Sgr","Dott","Prof","Avv","Ing","Geom","Rag","Arch","On","Egr","Spett","Gent","Ill")
HONORIFICS_ES = ("Sr","Sra","Sres","Sras","Srta","Srtas","Dr","Dra","Dres","Lic","Licda","Ing","Prof","Profa","Arq","Mtro","Mtra")
HONORIFICS_DE = ("Hr","Fr","Frl","Dr","Prof","Dipl","Mag")
HONORIFICS_FR = ("Mme","Mmes","Mlle","Mlles","MM","Dr","Pr","Mgr","Me")
HONORIFICS_PT = ("Sr","Sra","Srs","Sras","Srta","Srtas","Dr","Dra","Eng","Enga","Prof","Profa")

HONORIFICS_BY_LANGUAGE: dict[str, tuple[str, ...]] = {
    "en": HONORIFICS_EN, "it": HONORIFICS_IT, "es": HONORIFICS_ES,
    "de": HONORIFICS_DE, "fr": HONORIFICS_FR, "pt": HONORIFICS_PT,
}

HONORIFICS_ALL: tuple[str, ...] = tuple(
    sorted({p for prefixes in HONORIFICS_BY_LANGUAGE.values() for p in prefixes}, key=lambda s: (-len(s), s))
)

_SENTENCE_TERMINATORS = ".!?…;。！？；．｡"
_UNAMBIGUOUS_NON_LATIN_TERMINATORS = "।॥؟؛۔؏։፧።។៕။༎༏"
_TERMINATOR_REGEX_CLASS = "".join(re.escape(c) for c in sorted(set(_SENTENCE_TERMINATORS + _UNAMBIGUOUS_NON_LATIN_TERMINATORS)))
_SOFT_TERMINATORS = ",—–"
DEFAULT_AGGRESSIVE_FIRST_MIN_LEN = 40
_CURRENCY_SYMBOLS = "$€£¥₹₩"
_HONORIFICS_REGEX = "|".join(re.escape(p) for p in HONORIFICS_ALL)


def _split_sentences(text: str, *, min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN) -> list[tuple[str, int, int]]:
    alphabets = r"([A-Za-z])"
    prefixes = rf"({_HONORIFICS_REGEX})[.]"
    suffixes = r"(Inc|Ltd|Jr|Sr|Co|ecc|cit|cap|sez|art|pag|fig|tab|cfr|vol|ed|vs|etc|No|Vol|pp|cf|ca|op|Mt|Hwy|Rt|Pl|Ave|Blvd|Sq)"
    starters = r"(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
    acronyms = r"([A-Z][.][A-Z][.](?:[A-Z][.])?)"
    websites = r"[.](com|net|org|io|gov|edu|me)"
    digits = r"([0-9])"
    multiple_dots = r"\.{2,}"

    text = text.replace("\n", " ")
    text = re.sub(prefixes, r"\1<prd>", text)
    text = re.sub(websites, r"<prd>\1", text)
    text = re.sub(digits + r"[.]" + digits, r"\1<prd>\2", text)
    text = re.sub(multiple_dots, lambda m: "<prd>" * len(m.group(0)), text)
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub(r"\s" + alphabets + r"[.] ", r" \1<prd> ", text)
    text = re.sub(acronyms + r" " + starters, r"\1<stop> \2", text)
    text = re.sub(alphabets + r"[.]" + alphabets + r"[.]" + alphabets + r"[.]", r"\1<prd>\2<prd>\3<prd>", text)
    text = re.sub(alphabets + r"[.]" + alphabets + r"[.]", r"\1<prd>\2<prd>", text)
    text = re.sub(r" " + suffixes + r"[.] " + starters, r" \1.<stop> \2", text)
    text = re.sub(r" " + suffixes + r"[.]", r" \1<prd>", text)
    text = re.sub(r" " + alphabets + r"[.]", r" \1<prd>", text)
    text = re.sub(rf"([{_TERMINATOR_REGEX_CLASS}])([\"\u201d])", r"\1\2<stop>", text)
    text = re.sub(rf"([{_TERMINATOR_REGEX_CLASS}])(?![\"\u201d])", r"\1<stop>", text)
    text = text.replace("<prd>", ".")

    splitted = text.split("<stop>")

    sentences: list[tuple[str, int, int]] = []
    buff = ""
    start_pos = 0
    end_pos = 0

    for match in splitted:
        sentence = match.strip()
        if not sentence:
            continue
        buff += " " + sentence
        end_pos += len(match)
        if len(buff) > min_sentence_len:
            sentences.append((buff.lstrip(), start_pos, end_pos))
            start_pos = end_pos
            buff = ""

    if buff:
        sentences.append((buff.lstrip(), start_pos, len(text) - 1))

    return sentences


class SentenceChunker:
    """Accumulates streaming LLM tokens and yields complete sentences.

    Usage::

        chunker = SentenceChunker()
        async for token in groq_stream:
            for sentence in chunker.push(token):
                audio_chunks = await tts.synthesize(sentence)
        for sentence in chunker.flush():
            audio_chunks = await tts.synthesize(sentence)
    """

    def __init__(
        self,
        *,
        min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN,
        min_words_for_short_flush: int = DEFAULT_MIN_WORDS_FOR_SHORT_FLUSH,
        aggressive_first_flush: bool = False,
        aggressive_first_min_len: int = DEFAULT_AGGRESSIVE_FIRST_MIN_LEN,
        language: str = "en",
    ) -> None:
        self._buffer = ""
        self._min_sentence_len = min_sentence_len
        self._min_words_for_short_flush = min_words_for_short_flush
        self._aggressive_first_min_len = aggressive_first_min_len
        self._language = (language or "en").lower()
        self._aggressive_first_flush = (
            aggressive_first_flush and not self._language.startswith("it")
        )
        self._is_first_flush = True

    def push(self, token: str) -> list[str]:
        """Feed a token. Returns zero or more complete sentences."""
        self._buffer += token

        if self._aggressive_first_flush and self._is_first_flush:
            flushed = self._maybe_aggressive_first_flush()
            if flushed is not None:
                self._is_first_flush = False
                return [flushed]

        if len(self._buffer) < self._min_sentence_len:
            return self._maybe_short_flush()

        sentences = _split_sentences(self._buffer, min_sentence_len=self._min_sentence_len)

        if len(sentences) <= 1:
            return []

        result: list[str] = []
        for sent_text, _, _ in sentences[:-1]:
            if sent_text.strip():
                result.append(sent_text.strip())

        last_text = sentences[-1][0] if sentences else ""
        self._buffer = last_text

        if result:
            self._is_first_flush = False

        return result

    def _maybe_short_flush(self) -> list[str]:
        stripped = self._buffer.rstrip()
        if not stripped or stripped[-1] not in _SENTENCE_TERMINATORS:
            return []
        if sum(1 for c in stripped if c in _SENTENCE_TERMINATORS) != 1:
            return []
        word_count = len(stripped.split())
        if word_count < self._min_words_for_short_flush:
            return []
        if len(stripped) >= 2:
            prev = stripped[-2]
            if prev.isdigit():
                return []
            terminator = stripped[-1]
            last_word = (stripped.rstrip(_SENTENCE_TERMINATORS).split()[-1] if stripped.rstrip(_SENTENCE_TERMINATORS).split() else "")
            if terminator == "." and last_word.isascii() and last_word.isupper() and len(last_word) <= 3:
                return []
            if terminator == "." and last_word in HONORIFICS_ALL:
                return []
        self._buffer = ""
        return [stripped]

    def _maybe_aggressive_first_flush(self) -> str | None:
        rstripped = self._buffer.rstrip()
        if len(rstripped) < self._aggressive_first_min_len:
            return None
        last_char = rstripped[-1]
        if last_char not in _SOFT_TERMINATORS:
            return None
        pos = len(rstripped) - 1
        if pos + 1 >= len(self._buffer):
            return None
        next_char = self._buffer[pos + 1]
        if last_char == ",":
            prev_char = rstripped[pos - 1] if pos >= 1 else ""
            if prev_char.isdigit() and next_char.isdigit():
                return None
            tail = rstripped[max(0, pos - 6):pos]
            if prev_char.isdigit() and ("," in tail and any(c.isdigit() for c in tail)):
                return None
        snippet = rstripped[max(0, pos - 8):pos]
        if any(c in snippet for c in _CURRENCY_SYMBOLS):
            return None
        opens = sum(rstripped.count(c) for c in "([{")
        closes = sum(rstripped.count(c) for c in ")]}")
        if opens > closes:
            return None
        if rstripped.count('"') % 2 != 0:
            return None
        if rstripped.endswith("...") or rstripped.endswith("…"):
            return None
        if last_char == "," and next_char == '"':
            return None
        flushed = rstripped
        self._buffer = self._buffer[len(rstripped):].lstrip()
        return flushed

    def flush(self) -> list[str]:
        """Flush remaining buffer. Call at end of stream."""
        remaining = self._buffer.strip()
        self._buffer = ""
        self._is_first_flush = True
        if not remaining:
            return []
        return [remaining]

    def reset(self) -> None:
        """Discard buffered text. Call on interrupt/cancel."""
        self._buffer = ""
        self._is_first_flush = True
