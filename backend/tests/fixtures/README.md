# Test fixture'ları

Testler hiçbir dış servisi çağırmaz; bu dosyalar `respx` ile mock'lanan yanıtlardır.

| Dosya grubu | Kaynak | Not |
|---|---|---|
| `tmdb_*.json` | TMDB API v3 | Gerçek yanıtların şekli ve alan adları birebir; değerler temsili. |
| `dtdd_*.json` | DoesTheDogDie API v3 | Alan adları doğrulanmış listeyle sınırlı (`topicItemStats`, `topicId`, `topicName`, `yesSum`, `noSum`, `numComments`, `triggerDescription`, `cueDescription`, `position1/2/3`). Dış sarmalayıcı (`{"items": [...]}`) temsilidir; servis çıplak listeyi de kabul eder. |
| `imdb_parentalguide_*.html` | IMDb parents guide | **Elle kurulmuştur** (IMDb ToS gereği sayfa kazınmadı). `__NEXT_DATA__` iki farklı şekli kapsar: düz `noneVotes/mildVotes/...` (veri sözlüğü) ve GraphQL tarzı `severityBreakdown[]`. Parser sabit yol kullanmadığı için ikisini de bulmalıdır. |
| `imdb_waf_challenge.html` | AWS WAF | Challenge sayfası davranış testi. |
| `movie_map_*.html` | Movie-Map | Deneysel kaynak, temsili. |

Gerçek kayıtlı bir yanıt eklemek isterseniz aynı dosya adıyla değiştirin; testler şekle göre yazılmıştır.
