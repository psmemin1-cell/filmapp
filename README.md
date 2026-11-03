# CineScope

Film adını yaz → tek ekranda **puan**, **Türkiye'deki yayın platformları**, **içerik hassasiyeti
raporu** (odak: Sex & Nudity) ve **benzer filmler**.

| Modül | Teknoloji | Belge |
|---|---|---|
| [`backend/`](backend/) | Python 3.12 · FastAPI · httpx · Pydantic v2 | [backend/README.md](backend/README.md) |
| [`android/`](android/) | Kotlin · Compose · Hilt · Retrofit · kotlinx.serialization · Coil 3 | [android/README.md](android/README.md) |

API sözleşmesi tek doğruluk kaynağıdır: `backend/app/schemas/movie_response.py`. Android DTO'ları
(`android/app/src/main/java/com/cinescope/app/data/remote/dto/`) alan alan bunun karşılığıdır.

## Veri kaynakları ve lisans notları

- **TMDB** – künye, puan (`rating_source: "tmdb"`), TR yayın platformları (JustWatch), öneriler.
  *This product uses the TMDB API but is not endorsed or certified by TMDB.*
- **IMDb Parents Guide** – yalnızca geliştirme amaçlı scraper; IMDb Kullanım Koşulları veri
  madenciliğini yasaklar. Üretimde AWS Data Exchange'teki lisanslı veri seti kullanılmalıdır.
- **DoesTheDogDie** – "Powered by DoesTheDogDie.com" attribution'ı zorunludur; Free tier yalnızca
  ticari olmayan kullanım içindir, gelir elde eden uygulama için Commercial tier gerekir.

Ayrıntılar: [backend/README.md §5–6](backend/README.md).
