# CineScope Android

Kotlin + Jetpack Compose istemcisi. Paket `com.cinescope.app`, minSdk 26 / targetSdk 35.

| Katman | İçerik |
|---|---|
| `data/remote` | Retrofit `CineScopeApi`, kotlinx.serialization DTO'ları (backend sözleşmesinin birebir karşılığı) |
| `data/mapper` | DTO → domain; blok durumu `sources` **ve** alanın null'luğu birlikte kontrol edilerek belirlenir |
| `data/repository` | `MovieRepositoryImpl` (200 / 404 / hata ayrımı, API çağrısı loglanır: `adb logcat -s CineScopeRepo`) |
| `domain` | Saf Kotlin modeller, `Block<T>` (Ready / Missing), `MovieRepository` |
| `presentation` | `SearchViewModel` (StateFlow, 400 ms debounce), Compose bileşenleri, tema |
| `di` | Hilt modülleri (OkHttp, Retrofit, Json, repository) |

## Çalıştırma

1. Backend'i başlatın (`backend/README.md`): `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Android Studio (Ladybug veya üstü, JDK 17+) ile `android/` klasörünü açın ya da:

```bash
cd android
./gradlew assembleDebug
./gradlew testDebugUnitTest
```

Debug build `BASE_URL = http://10.0.2.2:8000/` kullanır (emülatörden host makineye). Fiziksel
cihaz için `app/build.gradle.kts` içindeki debug `buildConfigField` değerini bilgisayarınızın
yerel IP'si ile değiştirin ve aynı adresi `res/xml/network_security_config.xml`'e ekleyin.
Release adresi: `-PCINESCOPE_RELEASE_BASE_URL=https://...`.

## Lisans / attribution

- `ContentAdvisoryCard` her göründüğünde en altta, görünür ve tıklanabilir
  **"Powered by DoesTheDogDie.com"** bağlantısı (https://www.doesthedogdie.com) bulunur.
  Bu metin `strings.xml`'de `translatable="false"`; değiştirmeyin.
- DTDD Free tier yalnızca ticari olmayan kullanım içindir; uygulama gelir elde edecekse
  Commercial tier gerekir (bkz. `backend/README.md` §5).
- Yayın platformu verisi TMDB üzerinden JustWatch'tan gelir; `StreamingRow` bunu belirtir.
- Puan rozeti etiketi `rating_source` alanından gelir ("TMDB"); uygulamada "IMDb" puanı gösterilmez.
