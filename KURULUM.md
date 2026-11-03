# CineScope'u telefonda kullanma rehberi (Android)

Toplam süre: yaklaşık 20–30 dakika. Bilgisayar gerekmez, hepsi tarayıcıdan yapılabilir.

Uygulama iki parçadan oluşur:

- **Sunucu (backend):** film verisini TMDB, IMDb ve DoesTheDogDie'dan toplar. Render'da ücretsiz çalışır.
- **Uygulama (APK):** telefonda çalışan arayüz. GitHub sizin için otomatik derler.

---

## 1. API anahtarlarını alın (bir kez)

| Anahtar | Nasıl alınır |
|---|---|
| **TMDB** (zorunlu) | <https://www.themoviedb.org/signup> ile hesap açın → profil → **Ayarlar → API** → "Create / Request an API key" → *Developer* → formu doldurun. Size verilen **API Key (v3)** değerini kopyalayın. |
| **DoesTheDogDie** (önerilir) | <https://www.doesthedogdie.com> → hesap açın → profil sayfasındaki **API** bölümünden anahtarı kopyalayın. Yoksa uygulama çalışır, yalnızca "Topluluk yanıtları" bölümü "veri yok" gösterir. |

> DoesTheDogDie'ın ücretsiz anahtarı **yalnızca ticari olmayan kullanım** içindir. Uygulamadan para
> kazanmayı düşünürseniz Commercial plan gerekir.

## 2. Sunucuyu Render'da yayınlayın (bir kez)

1. <https://dashboard.render.com/register> adresinde **GitHub ile kaydolun**.
2. Panelde **New → Blueprint**'e tıklayın.
3. Depo listesinden **`psmemin1-cell/filmapp`** deposunu seçin.
   Dal (branch) sorulursa: `claude/intelligent-maxwell-wy2enp`.
4. Render, repodaki `render.yaml` dosyasını okuyup **cinescope-api** servisini gösterir.
   `TMDB_API_KEY` ve `DTDD_API_KEY` alanlarına 1. adımdaki anahtarları yapıştırın.
5. **Apply / Deploy Blueprint**'e tıklayın. İlk kurulum 3–5 dakika sürer.
6. Bitince servis sayfasının üstünde adresiniz görünür, örneğin
   `https://cinescope-api.onrender.com`. **Bu adresi kopyalayın.**
7. Kontrol: telefon tarayıcısında şu adresi açın (kendi adresinizle):
   `https://cinescope-api.onrender.com/api/v1/movies/search?title=Oppenheimer`
   Ekranda film bilgilerini içeren uzun bir metin görüyorsanız sunucu hazır.

> **Ücretsiz plan notu:** Sunucu 15 dakika kullanılmazsa uykuya geçer. Uygulamayı açınca kendiliğinden
> uyandırılır; uzun bir aradan sonraki ilk arama 30–60 saniye sürebilir, sonrakiler hızlıdır.

## 3. Telefon APK'sını üretin

1. <https://github.com/psmemin1-cell/filmapp/actions/workflows/android.yml> sayfasını açın.
2. Sağdaki **Run workflow** düğmesine tıklayın.
3. Dal olarak `claude/intelligent-maxwell-wy2enp` seçin, **api_base_url** kutusuna 2. adımdaki
   adresi yapıştırın (ör. `https://cinescope-api.onrender.com/`) ve **Run workflow**'a basın.
4. 3–5 dakika bekleyin; çalışma yeşil ✓ olunca üzerine tıklayın.
5. Sayfanın altındaki **Artifacts** bölümünden **`cinescope-phone-apk`** dosyasını indirin.

**Her seferinde adres girmemek için (önerilir):** Repo → **Settings → Secrets and variables →
Actions → Variables → New repository variable** → ad: `CINESCOPE_API_URL`, değer: sunucu adresiniz.
Bundan sonra `android/` klasöründeki her değişiklikte telefon APK'sı otomatik üretilir.

## 4. Telefona kurun

1. İndirdiğiniz `cinescope-phone-apk.zip` dosyasını telefonda **Dosyalar** uygulamasıyla açın ve
   **Çıkart**'a dokunun. İçinden `CineScope-<numara>.apk` çıkar.
2. APK dosyasına dokunun. Android "bilinmeyen uygulamalar" uyarısı verirse
   **Ayarlar → Bu kaynağa izin ver**'i açın ve geri dönün.
3. **Yükle**'ye dokunun. Google Play Protect uyarı gösterirse **Yine de yükle**'yi seçin
   (uygulama Play Store'dan gelmediği için bu uyarı normaldir).
4. Ana ekranda **CineScope** ikonu belirir. Açın ve bir film adı yazın.

## 5. Güncelleme

Yeni bir APK ürettiğinizde 4. adımı tekrarlayın; uygulama verisi silinmeden eskisinin üzerine kurulur.
"Uygulama yüklenmedi" hatası alırsanız eski CineScope'u kaldırıp yenisini kurun (imza anahtarı
değişmişse olur; aşağıdaki kalıcı imza bunu tamamen önler).

### Opsiyonel: kalıcı imza anahtarı

GitHub derleme sunucuları imza anahtarını önbellekte tutar; bu önbellek uzun süre kullanılmazsa
silinebilir. Kalıcı bir anahtar için Java yüklü bir bilgisayarda:

```bash
keytool -genkeypair -v -keystore cinescope.jks -alias cinescope -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 cinescope.jks > cinescope.jks.b64
```

Ardından repo → **Settings → Secrets and variables → Actions → Secrets** altında şu dördünü ekleyin:
`CINESCOPE_KEYSTORE_BASE64` (b64 dosyasının içeriği), `CINESCOPE_KEYSTORE_PASSWORD`,
`CINESCOPE_KEY_ALIAS` (`cinescope`), `CINESCOPE_KEY_PASSWORD`. `cinescope.jks` dosyasını güvenli
bir yerde saklayın ve asla repoya koymayın.

---

## Sorun giderme

| Belirti | Neden / çözüm |
|---|---|
| İlk arama çok uzun sürüyor | Sunucu uykudan uyanıyor; bir dakika bekleyin veya **Yeniden dene**'ye basın. |
| "Bağlantı kurulamadı" | Telefonun internetini kontrol edin. Sunucu adresini tarayıcıda açıp (2.7) çalıştığını doğrulayın. |
| "Film servisine şu an ulaşılamıyor" | TMDB anahtarı yanlış/eksik olabilir. Render → cinescope-api → **Environment**'ı kontrol edin. |
| İçerik hassasiyeti kartında IMDb bölümü "veri yok" | IMDb, veri merkezlerinden gelen istekleri sık sık engeller; bu beklenen bir durumdur ve diğer bölümler çalışmaya devam eder. Kalıcı çözüm lisanslı IMDb veri setidir (bkz. `backend/README.md` §6). |
| "Topluluk yanıtları" bölümü "veri yok" | `DTDD_API_KEY` girilmemiş ya da aylık kota dolmuş olabilir. |
| Uygulama yüklenmiyor | 5. adımdaki "Uygulama yüklenmedi" açıklamasına bakın. |
