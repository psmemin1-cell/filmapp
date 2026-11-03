"""DoesTheDogDie cinsellik/çıplaklık konu eşleşmeleri.

DTDD topic ID'leri sabit olmadığı için ID gömülmez; konular GET /topics yanıtındaki
`name` alanına göre bu desenlerle eşleştirilir. İlk çağrıda doğrulanır: eşleşmeyen
anahtar varsa uyarı loglanır (DTDD konu adlarını değiştirmiş olabilir).

Sıra önemlidir: "sexual assault" hem `sexual_assault` hem `sex_scene` desenine
uyabileceği için daha özel desen önce gelir; her topic yalnızca ilk eşleşen anahtara
atanır.
"""

from __future__ import annotations

import re

# (topic_key, desen). topic_key yanıtta `community[].topic_key` olarak döner ve Android
# tarafında strings.xml anahtarına çevrilir.
SENSITIVE_TOPIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "sexual_assault",
        re.compile(r"sexual(ly)? assault|sexual(ly)? abuse|\brap(e|ed|ist)\b", re.I),
    ),
    ("nudity", re.compile(r"\bnud(e|ity)\b|\bnaked\b", re.I)),
    ("sex_scene", re.compile(r"\bsex\b|sex scene|sexual content|\bsexual\b", re.I)),
)

TOPIC_KEYS: tuple[str, ...] = tuple(key for key, _ in SENSITIVE_TOPIC_PATTERNS)

# Yanıttaki görüntüleme sırası (eşleştirme sırasından bağımsız).
DISPLAY_ORDER: tuple[str, ...] = ("nudity", "sex_scene", "sexual_assault")


def match_topic_key(name: str | None) -> str | None:
    if not name:
        return None
    for key, pattern in SENSITIVE_TOPIC_PATTERNS:
        if pattern.search(name):
            return key
    return None
