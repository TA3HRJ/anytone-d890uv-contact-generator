# HANDOFF

Son güncelleme: 2026-09-08

## Nerede kalındı

Yedi iş bitti ve gerçek veriyle doğrulandı:

### 1. Avrupa/Türkiye filtresi artık MCC'ye bakıyor

**Sorun neydi:** filtre yalnızca `COUNTRY` sütunundaki serbest metne bakıyordu ve radioid.net'in
yazımıyla tutmuyordu. Ölçülen kayıp: `Bosnia and Hercegovina` (558), `Luxemburg` (249),
`Macedonia` (142), `Corsica`, `Gibraltar`, `Faroe Islands`, `Aaland Islands`. Sette olup veride
hiç geçmeyen 6 isim de vardı (`Czechia`, `Turkey`, `Vatican City`…) — liste hiç doğrulanmamıştı.

**Ne yapıldı:** DMR ID'sinin ilk üç hanesi MCC ülke kodu ve `2xx` bloğu tamamen Avrupa'ya
ayrılmış. Artık birincil ölçüt bu (`is_european_id`, `is_turkish_id`). Ülke adı eşleşmesi yalnızca
MCC 2xx dışında kalan Avrupa ülkeleri (Azerbaycan 400, Kazakistan 401) için yedek olarak duruyor,
ama normalize edilerek (`normalize_country`: unidecode + küçük harf + boşluk sadeleştirme) ve
eksik yazımlar `EUROPE_COUNTRIES`'e eklenerek.

**Tuzak:** NXDN ID'leri MCC taşımıyor (1-5 hane). Orada tek ölçüt hâlâ ülke adı — bu yüzden
`EUROPE_COUNTRIES`'teki yazım listesi silinemez, MCC onun yerine geçmez.

**Kazanç (2026-09-07 verisiyle ölçüldü):** DMR Avrupa 113.266 → 114.292 (+1.026; bunun 1.021'i
yazım varyantı, 5'i radioid'de ülkesi yanlış girilmiş 2xx ID'li kayıt). NXDN Avrupa
6.031 → 6.064 (+33) — burada MCC yok, kazancın tamamı yazım listesinden geliyor.

**Erken uyarı:** `report_country_gaps()` her çalıştırmada "MCC'ye göre Avrupa ama adı listede
yok" diyen ülkeleri yazdırıyor. radioid bir ülkenin yazımını değiştirdiğinde bu satır çıkar ve
NXDN tarafındaki sessiz kaybı haber verir. Şu an yalnızca radioid'de ülkesi yanlış girilmiş
5 kayıt görünüyor (US 3, Canada 2 — 2xx ID'li), yani liste temiz.

### 2. Bozuk indirme artık sağlam çıktının üzerine yazmıyor

Üç katman, hepsi CSV yazmadan **önce** çalışıyor:

- `download()` artık `timeout=120` ile çağrılıyor ve ağ hatasında `sys.exit`.
- `require_csv()` gövdenin başlık satırında `RADIO_ID`/`CALLSIGN`/`COUNTRY` arıyor —
  radioid 200 ile HTML hata sayfası döndürdüğünde burada duruyor.
- `check_sanity()` sayıları bir önceki çalışmayla karşılaştırıyor; herhangi bir liste
  %80'in (`MIN_RATIO`) altına düşerse hata. Taban yoksa `ABSOLUTE_FLOORS` devreye giriyor.

**Kritik ayrıntı — taban nereden geliyor:** CI'da `output/` gitignore'da, yani orada yerel
`stats.json` hiç yok. Bu yüzden `load_baseline()` yerelde bulamazsa yayındaki Pages kopyasını
(`BASELINE_STATS_URL`) çekiyor. Bu olmadan kontrol CI'da hiç ateşlenmezdi. Pages'e ulaşılamazsa
sessizce mutlak sınırlara düşüyor, işi durdurmuyor.

Her iki senaryo elle doğrulandı: HTML gövde ve yarılanmış kaynak denendi, ikisinde de script
hata verdi ve `output/` altındaki dosyaların md5'leri değişmedi.

### 3. Testler

`tests/test_generator.py`, 85 test. Kapsanan üç kırılgan nokta: 16 karakter sınırı,
CPS sütun düzeni (başlıklar + QUOTE_ALL + CRLF), sayı kontrolü. Ayrıca ülke yazım
varyantları, MCC ön ekleri, yinelenen/geçersiz satır atma, harf çevirisi.

`requirements-dev.txt` eklendi. Workflow artık `generator.py`'den **önce** `pytest`
çalıştırıyor ve `timeout-minutes: 20` taşıyor.

### 4. İndirme sayfasındaki sayılar tarih damgasıyla aynı sürüme bağlandı

**Sorun neydi:** sayfa ve `stats.json` GitHub Pages tarafından bağımsız önbellekleniyor — ikisi de
`max-age=600` ama `Age`'leri ayrı ilerliyor (ölçüldü: sayfa `Age: 0` iken `stats.json` `Age: 20`).
Tarih damgası HTML'e build'de gömülü, sayılar ayrı bir `fetch` ile geliyordu; sayfa tazelenip yeni
"Last generated" tarihini gösterirken sayılar on dakikaya kadar bir önceki çalıştırmanınki
kalabiliyordu.

**Ne yapıldı:** `fetch("stats.json?v={{VERSION}}")`, `{{VERSION}}` build adımında
`date -u +%Y%m%d%H%M` ile damgalanıyor. HTML ve sayılar artık hep aynı sürümden geliyor.
Yayında doğrulandı: damga `2026-09-07 20:12 UTC`, istek `stats.json?v=202609072012`.

**Kalan davranış (hata değil):** HTML'in kendisi hâlâ 10 dakikaya kadar önbellekte kalabiliyor,
yani geri dönen ziyaretçi bir süre önceki sayfayı görebilir. Fark şu ki artık o sayfadaki tarih ve
sayılar birbiriyle tutarlı.

### 5. CI bakımı ve görüntü düzeltmeleri

- Dört action güncel majör sürüme çekildi (checkout v7, setup-python v7,
  upload-pages-artifact v5, deploy-pages v5). Eski sürümler Node 20 hedefliyordu;
  runner şimdilik Node 24'e zorluyor ama destek kalkınca üretim dururdu.
- Workflow'a `concurrency: group: pages, cancel-in-progress: false` eklendi.
- İsmi boş 39 kayıtta `Name` alanına çağrı işareti konuyor.
- `normalize_case()` — CAPS LOCK / tamamen küçük harf düzeltmesi. **Neden sadece
  tek biçim kutulanmış parçalara uygulanıyor:** körlemesine `.title()` kaynakta
  zaten doğru yazılmış 25 ismi (McDonald, MacKenzie, LaSalle) ve isim alanına
  yazılmış 2.925 çağrı işaretini (K2BSA -> K2bsa) bozuyordu. Rakam içeren parça
  ve karışık kutulu parça atlanıyor; baş harfler `title()` sayesinde
  kendiliğinden korunuyor, ayrı kural gerekmiyor (ilk denemede 1-2 harf koruması
  konmuştu, "PALMA DE MALLORCA" -> "Palma DE Mallorca" verdiği için kaldırıldı).
  **Ülke alanı kasıtlı olarak dışarıda** — bölge filtresi o değere bakıyor.
  Ekran görüntüsüyle doğrulandı: `ESMERALDO/FORTALEZA` -> `Esmeraldo/Fortaleza`,
  `carlos/ribeirao pires` -> `Carlos/Ribeirao Pires`, `McKinney` ve `LaSalle`
  bozulmadan duruyor.

### 6. Üretim başarısız olunca issue açılıyor

Zamanlanmış çalıştırma sessizce başarısız olduğunda hiçbir uyarı çıkmıyordu.
Actions ve Deployments sekmeleri mobilde görünmediği için uyarının Issues sekmesinde
durması gerekiyordu.

`notify-failure` işi (`if: failure()`, `permissions: issues: write`) başarısız
çalıştırmayı `uretim-hatasi` etiketiyle bir issue olarak açıyor. Aynı arıza günlerce
sürerse yeni issue açmıyor, açık olana yorum düşüyor — bunun için etiketle
eşleştiriliyor, başlık aramasıyla değil (arama indeksi gecikebiliyor).

**Gerçekten test edildi.** Geçici bir dalda kasten hata veren bir adımla iki kez
çalıştırıldı: ilkinde issue açıldı, ikincisinde yeni issue açılmayıp yoruma düşüldü.
Üretim etkilenmedi (`deploy` işi hiç koşmadı). Test dalı ve issue temizlendi;
Actions geçmişinde iki başarısız çalıştırma kaydı bu yüzden duruyor.

### 7. Üretim tarihi stats.json'a taşındı, sayfa artık build'de yamalanmıyor

Tarih HTML'e `sed` ile gömülüyor, sayılar ayrı bir istekle geliyordu; ikisi ayrı
önbelleklendiği için taze tarih eski sayılarla görünebiliyordu (bkz. 4. iş). Buna karşı
`fetch`'e ikinci bir `sed` ile sürüm anahtarı basılmıştı.

Tarih artık `stats.json` içinde (`generated_at`). Sayfa ikisini **tek istekte** aldığı için
ayrışma yapısal olarak imkânsız; sürüm anahtarına gerek kalmadı ve build adımı üç kopyalama
komutuna indi. `index.html` depodaki hâliyle yayınlanabilir durumda.

**Eski tuzak kapatıldı:** sayfa `stats.json`'daki anahtarları artık körlemesine dolaşmıyor,
beklediği alanları tek tek okuyor. `generated_at` eklenmesi eskiden `null.textContent` ile
scripti patlatıp tablodaki bütün sayıları `-` bırakırdı. Sözleşme teste bağlandı: her sayının
sayfada bir hücresi olduğu, tarih için yer bulunduğu ve sayfada doldurulmamış yer tutucu
kalmadığı doğrulanıyor (89 test).

## Ölçülen sonuç (2026-09-07 verisi)

| Liste | Kayıt |
|---|---|
| DMR Türkiye | 8.385 |
| DMR Avrupa | 114.292 |
| DMR Dünya | 312.827 |
| NXDN Türkiye | 646 |
| NXDN Avrupa | 6.064 |
| NXDN Dünya | 17.606 |

## Açık kalanlar

Öncelik sırasıyla:

1. **Büyük dosyaları gzip/zip sunmak** — DMR Dünya 31 MB. Kullanıcı 2026-09-08'de
   "şimdilik pas" dedi; sıkıştırma indirmeyi hızlandırır ama kullanıcıya bir adım ekler.
2. **Ülke seçmeli üretim** — veride 186 ülke var; her ülke için ayrı CSV + sitede seçici.
   **Bilinçli olarak ertelendi (2026-09-07).** Kullanıcının koyduğu sınır: indirme sayfasının
   sade ve işlevsel tasarımı zarar görmemeli. 186 satırlık bir liste ya da ağır bir seçici
   arayüz bu şartı çiğner; iş yeniden ele alınırken önce tasarımın nasıl korunacağı
   çözülmeli, üretim tarafı ondan sonra gelir.

## Yapılmamasına karar verilenler

**Talkgroup listesi üretmek (2026-09-08'de kapatıldı).** Uzun süre "deponun eksik ikinci
yarısı" diye listede duruyordu; ölçünce iki ayrı sebepten kötü bir fikir olduğu çıktı.

*Sıralama bağlılığı:* CPS'te kanallar ve zone'lar TG'lere sıra numarasıyla bağlı. Üretilen
liste mevcut listenin üzerine yazıldığında her kanal başka bir TG'yi gösterir. Kullanıcının
listesinde ayrıca RadioID'ler `Private Call` + `Ring` olarak TG'ymiş gibi kayıtlı (direkt
çağrı için); üretilen hiçbir liste bunları bilemez.

*Kaynak veri yetersiz:* kullanıcının listesinden 29 TG örneklendi, Brandmeister'da yalnızca
15'i vardı. Eksikler arasında TGIF ağının TG'leri (111/113/114/123 — BM'de değil, ayrı ağ),
bazı Türkiye il TG'leri (2863, 28660), köprü/servis TG'leri (66860 TR YSF, 262999 APRS,
284997 Echolink) ve yerel olanlar (286911 AFET 2, 2862012 AKRAD) var. Var olanlarda bile
adlandırma tutmuyor: `TG28635 Izmir` yerine `Türkiye Izmir`, `PC4000 Disconnec` yerine
`Disconnect`.

*Asıl ayrım:* kişi listesi kişisel değil — 312.827 kayıt, her gün değişiyor, herkes için
aynı; otomasyonun tam yeri. TG listesi kişisel — ~117 satır, neredeyse hiç değişmiyor,
içeriği ve sırası kullanıcının kanal kurgusuna bağlı. Otomasyon burada az kazandırıp çok
riske atıyor.

Yine de yapılacaksa tek makul biçim şu: mevcut TG dosyasını girdi alıp **yalnızca sona
ekleyen** bir birleştirici — indeksler korunur. Site üzerinden dağıtılan bir liste değil,
elle beslenen bir araç olur ve yukarıdaki eksik veri sorunu yine devam eder.

CPS dışa aktarma formatları (ileride lazım olursa, cihazdan alındı):
- DMR: `"No.","Radio ID","Name","Call Type","Call Alert"` — ad 16 karakter, `Call Type`
  satır bazında `Group Call` / `Private Call`.
- NXDN: başlık kişi listesiyle birebir aynı; ayrım `Attr` sütununda (TG'de `1`, kişide `0`).
  Sıra sütunu yok, `FIRST_NAME` 16 karaktere boşlukla dolduruluyor.
