# CineScope Backend (FastAPI)

Tek uç nokta: kullanıcı film adı yazar, tek yanıtta **künye + TMDB puanı**, **Türkiye yayın
platformları**, **içerik hassasiyeti raporu** (odak: Sex & Nudity) ve **5 benzer film** döner.

```
GET /api/v1/movies/search?title={query}
```

Yanıt sözleşmesi: [`app/schemas/movie_response.py`](app/schemas/movie_response.py) (tek doğruluk
kaynağı; Android DTO'ları buradan türetilir). Canlı şema: `http://localhost:8000/docs`.

---

## 1. Kurulum

Gereksinim: Python 3.12+.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt     # yalnızca çalıştırmak için: requirements.txt
cp .env.example .env                    # ardından anahtarları doldurun
```

### API anahtarları

| Değişken | Nereden alınır |
|---|---|
| `TMDB_API_KEY` | <https://www.themoviedb.org> → hesap oluştur → **Settings → API** → "Request an API Key" (Developer). v3 *API Key* veya v4 *API Read Access Token* (`eyJ...`) kullanılabilir; ikisi de otomatik tanınır. |
| `DTDD_API_KEY` | <https://www.doesthedogdie.com> → hesap oluştur → profil sayfasındaki **API** bölümü. Free tier: dakikada 30, ayda 5.000 istek; **yalnızca ticari olmayan kullanım**. |

Gerçek anahtarları hiçbir dosyaya commit etmeyin; `.env` kök `.gitignore` içinde.

### Diğer ayarlar (`.env`)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `ENABLE_MOVIE_MAP` | `false` | Deneysel ikincil benzer film kaynağı. |
| `PARENTS_GUIDE_PROVIDER` | `scraper` | `scraper` (geliştirme) veya `dataset` (lisanslı veri seti). |
| `PARENTS_GUIDE_DATASET_PATH` | – | `dataset` için JSONL dökümü. |
| `CACHE_TTL_SECONDS` | `21600` | Tam yanıt cache süresi (6 saat). |
| `DEGRADED_CACHE_TTL_SECONDS` | `300` | En az bir kaynağı `unavailable` olan yanıtlar için. |
| `LOG_LEVEL` | `INFO` | JSON satırı formatında yapılandırılmış log. |
| `CORS_ALLOW_ORIGINS` | `*` | Virgülle ayrılmış liste. |

## 2. Çalıştırma

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: <http://localhost:8000/docs>
- Sağlık: <http://localhost:8000/health>
- Android emülatörü backend'e `http://10.0.2.2:8000/` üzerinden erişir.

## 3. Test ve kalite kapıları

```bash
pytest                    # hiçbir dış servis çağrılmaz (respx, assert_all_mocked)
ruff check .
ruff format --check .
```

Fixture'lar `tests/fixtures/` altında; nasıl oluşturulduklarını `tests/fixtures/README.md`
açıklar.

## 4. Mimari

```
routes.py ──► Aggregator ──► Aşama 1 (sıralı):   TMDB search → TMDB details (+external_ids)
                         └─► Aşama 2 (paralel): watch/providers · ParentsGuideProvider ·
                                                DTDD · recommendations (→ Movie-Map fallback)
```

- **Tek `httpx.AsyncClient`** lifespan'de açılır, `api/deps.py` ile tüm servislere enjekte edilir.
- **Zaman bütçesi:** dış istek başına 6 sn, toplam 12 sn. Bütçe dolarsa eldeki bloklarla dönülür,
  yetişmeyen kaynak `unavailable` olur.
- **Kısmi bozulma:** yalnızca TMDB isteği düşürebilir (`404 movie_not_found`, `503 upstream_unavailable`).
  Diğer kaynakların hataları `sources` alanına yazılır (`ok | unavailable | not_found | fallback`)
  ve ilgili blok `null` olur; yanıt yine `200`.
  - `streaming_tr` TMDB'den gelir; ayrı watch/providers çağrısı düşerse `streaming_tr: null`
    olur, `sources.tmdb` ise künye geldiği için `ok` kalır. İstemci her iki alanı birlikte kontrol etmelidir.
  - `similar`: önce TMDB `recommendations`; boşsa ve `ENABLE_MOVIE_MAP=true` ise Movie-Map
    (`fallback`); hiçbiri yoksa `not_found` ve `similar: null`.
- **Cache:** `CacheBackend` async protokolü (Redis'e geçişe hazır), başlangıçta
  `cachetools.TLRUCache`. Anahtarlar: `search:{normalize edilmiş başlık}` ve `movie:{tmdb_id}`
  (farklı yazımlar aynı filme çözülünce dış kaynaklar tekrar çağrılmaz). DTDD sonuçları ayrıca
  `dtdd:item:{imdb_id}` altında cache'lenir. Aynı film için eşzamanlı istekler tek hesaplamada
  birleştirilir.
- **Severity** oyların **medyanıdır** (ortalama değil); `vote_breakdown` 0–1 arası oranlardır,
  toplamı 1.0'dır.

### Sözleşmeye yapılan tek ekleme

`content_advisory.community[].topic_key` (`"nudity" | "sex_scene" | "sexual_assault"`):
DTDD konu ID'leri sabit olmadığı ve backend çeviri yapmadığı için Android, soruyu bu kararlı
anahtarla `strings.xml` üzerinden Türkçeleştirir. `question` alanı DTDD'nin özgün metnini taşır
(eşleşme olmazsa istemci onu gösterir). Mevcut hiçbir alan değişmedi.

## 5. DoesTheDogDie lisans ve attribution notu (ZORUNLU)

1. **Attribution:** DTDD verisinin göründüğü her ekranda, tam olarak
   **"Powered by DoesTheDogDie.com"** ifadesi, <https://www.doesthedogdie.com> adresine link'li ve
   menü/tooltip arkasında değil **görünür** şekilde yer almalıdır. API bu metni
   `content_advisory.attribution` alanında döndürür; Android `ContentAdvisoryCard` her zaman gösterir.
2. **Ticari kullanım:** DTDD **Free tier yalnızca ticari olmayan kullanım içindir.** Uygulama
   reklam, abonelik, uygulama içi satın alma veya başka bir yolla **para kazanacaksa Commercial
   tier zorunludur.** Yayına almadan önce DTDD ile lisans anlaşması yapın.
3. Free tier kotası (30/dk, 5.000/ay) nedeniyle cache opsiyonel değildir; film başına en fazla
   5 DTDD isteği yapılır, 429'da `Retry-After` süresince DTDD hiç çağrılmaz.

## 6. IMDb scraping uyarısı ve lisanslı alternatif

> **UYARI:** IMDb [Kullanım Koşulları](https://www.imdb.com/conditions) veri madenciliğini,
> robotları ve ekran kazımayı (scraping) yasaklar. `ImdbScraperProvider` yalnızca yerel geliştirme
> ve prototip içindir; **üretimde kullanmayın.**

- Scraper `__NEXT_DATA__` JSON'unu okur (sabit yol yok, özyinelemeli arama), bulamazsa
  selectolax HTML fallback'ine geçer. AWS WAF challenge, 403/429 veya veri bulunamaması
  durumunda isteği düşürmez; `sources.imdb_parents_guide` `unavailable`/`not_found` olur.
  En fazla 1 retry (yalnızca timeout/5xx).
- **Üretim yolu:** AWS Data Exchange üzerindeki lisanslı
  **"IMDb Parents Guides: Severity Ratings & On-Screen Descriptions"** veri seti
  (190.000+ başlık, günlük güncel). Kod `ParentsGuideProvider` protokolü arkasındadır:
  `PARENTS_GUIDE_PROVIDER=dataset` ve `DatasetParentsGuideProvider`'a gerçek depolamaya
  (S3/Athena, Postgres…) bağlanan bir `DatasetLookup` vermek yeterlidir. Kayıt, scraper ile aynı
  ayrıştırıcıdan geçer.

## 7. Doğrulanamayan varsayımlar

Bu ortamdan DTDD, IMDb ve Movie-Map dokümantasyonuna/sayfalarına erişilemedi. Kod yalnızca
proje tanımında doğrulanmış uç nokta ve alan adlarını kullanır; aşağıdakiler savunmacı
ayrıştırılır ve ilk gerçek anahtarla doğrulanmalıdır:

- DTDD yanıt sarmalayıcısı (çıplak liste mi `{"items": [...]}` mi) — ikisi de kabul edilir.
- DTDD `/topics` öğelerinde `id` + `name` alanları; konu adı desenleri `app/services/dtdd_topics.py`.
  Eşleşmeyen anahtar olursa açılışta `dtdd_topic_keys_unmatched` uyarısı loglanır.
- Movie-Map URL şeması ve `#gnodMap a` seçicisi (özellik varsayılan kapalı).

## 8. Manuel kabul senaryoları

Gerçek anahtarlarla backend çalışırken:

```bash
# Türkiye'de yayında olan film -> streaming_tr.available: true, en az bir platform + logo
curl -s 'localhost:8000/api/v1/movies/search?title=Oppenheimer' | python -m json.tool

# Türkçe karakter / kısmi arama
curl -s 'localhost:8000/api/v1/movies/search?title=Y%C3%BCz%C3%BCklerin%20Efendisi'

# Türkiye'de yayında olmayan film -> streaming_tr.available: false (Android: "Türkiye yayın akışında bulunmuyor")
curl -s 'localhost:8000/api/v1/movies/search?title=<TR%27de%20olmayan%20film>'

# Hiç bulunamayan film -> 404 {"detail":"movie_not_found","query":"..."}
curl -s -w '\n%{http_code}\n' 'localhost:8000/api/v1/movies/search?title=zzqxqzzqx'

# Cache: ikinci çağrı "cached": true ve < 200 ms
time curl -s -o /dev/null 'localhost:8000/api/v1/movies/search?title=Oppenheimer'
```
