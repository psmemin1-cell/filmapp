"""Lisanslı IMDb Parents Guide veri seti sağlayıcısı (üretim yolu).

Kaynak: AWS Data Exchange - "IMDb Parents Guides: Severity Ratings & On-Screen
Descriptions" (190.000+ başlık, günlük güncel).

Bu modül veri setinin nasıl depolandığından (S3 + Athena, Postgres, yerel JSONL...)
bağımsızdır: `DatasetLookup` imdb_id için IMDb veri sözlüğü şeklindeki kaydı döndürür
(kategori başına severity + noneVotes/mildVotes/moderateVotes/severeVotes + açıklamalar).
Kayıt, scraper ile aynı `extract_categories` ayrıştırıcısından geçer; böylece iki
sağlayıcı aynı çıktıyı üretir.

Veri setine abone olunduğunda yapılacak tek iş, gerçek depolamaya bağlanan bir
`DatasetLookup` yazıp `PARENTS_GUIDE_PROVIDER=dataset` ile etkinleştirmektir.
`JsonlDatasetLookup` yerel bir JSONL dökümü için hazır implementasyondur.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

from app.core.errors import SourceNotFound, SourceUnavailable
from app.services.parents_guide.base import ParentsGuideResult
from app.services.parents_guide.scraper import extract_categories

logger = logging.getLogger(__name__)

SOURCE = "imdb_parents_guide"


class DatasetLookup(Protocol):
    async def get(self, imdb_id: str) -> dict[str, Any] | None: ...


class JsonlDatasetLookup:
    """Her satırı {"imdb_id": "tt...", ...} olan JSONL dosyasını belleğe indeksler."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._index: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        with self._path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    logger.warning("dataset_bad_row", extra={"line": line_no})
                    continue
                imdb_id = row.get("imdb_id") or row.get("tconst")
                if isinstance(imdb_id, str):
                    index[imdb_id] = row
        return index

    async def get(self, imdb_id: str) -> dict[str, Any] | None:
        if self._index is None:
            if not self._path.is_file():
                raise SourceUnavailable(SOURCE, "dataset_file_missing")
            self._index = self._load()
        return self._index.get(imdb_id)


class DatasetParentsGuideProvider:
    name = "imdb_dataset"

    def __init__(self, lookup: DatasetLookup | None) -> None:
        self._lookup = lookup

    async def fetch(self, imdb_id: str) -> ParentsGuideResult:
        if self._lookup is None:
            raise SourceUnavailable(SOURCE, "dataset_not_configured")
        try:
            record = await self._lookup.get(imdb_id)
        except SourceUnavailable:
            raise
        except Exception as exc:  # depolama katmanı hataları kaynağı düşürmemeli
            raise SourceUnavailable(SOURCE, f"dataset_error {type(exc).__name__}") from exc
        if not record:
            raise SourceNotFound(SOURCE, "title_not_in_dataset")
        categories = extract_categories(record)
        if not categories:
            raise SourceNotFound(SOURCE, "no_categories")
        return ParentsGuideResult(imdb_id=imdb_id, categories=categories)
