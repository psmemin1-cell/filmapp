"""Metin normalizasyonu yardımcıları."""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_FOLD_TABLE = str.maketrans(
    {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"}
)


def normalize_title(value: str) -> str:
    """Cache anahtarı için başlığı normalize eder.

    Küçük harfe çevirir (Türkçe karakterler korunur), fazla boşlukları temizler.
    'İ' harfi Python'da 'i̇' (birleşik nokta) ürettiği için önce 'i'ye çevrilir.
    """
    text = unicodedata.normalize("NFC", value).replace("İ", "i").lower()
    return _WS_RE.sub(" ", text).strip()


def fold_title(value: str) -> str:
    """Karşılaştırma için Türkçe karakterleri ASCII'ye katlar ("Kış" == "kis")."""
    text = normalize_title(value).translate(_FOLD_TABLE)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text)
    return _WS_RE.sub(" ", text).strip()
