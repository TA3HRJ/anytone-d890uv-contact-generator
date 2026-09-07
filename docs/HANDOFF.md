# HANDOFF

Son güncelleme: 2026-09-07

## Nerede kalındı

Beş iş bitti ve gerçek veriyle doğrulandı:

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

Öncelik sırasıyla, hiçbiri başlanmadı:

1. **Workflow başarısız olunca bildirim yok** — liste sessizce eskir.
2. **Büyük dosyaları gzip/zip sunmak** — DMR Dünya 31 MB.
3. **`stats.json`'a üretim tarihi koyup build'deki iki `sed`'i (`{{GENERATED_DATE}}`,
   `{{VERSION}}`) kaldırmak.** DİKKAT: `index.html` `stats.json`'daki *her* anahtarı
   `getElementById(k)` ile arıyor; karşılığı olmayan bir anahtar eklenirse script
   `null.textContent` ile patlar ve tablodaki bütün sayılar `-` kalır. Anahtar eklerken
   `index.html` aynı commit'te güncellenmeli. Ayrıca sürüm anahtarını kaldırmak 4. maddedeki
   önbellek ayrışmasını geri getirir — yerine `cache: "no-cache"` gibi bir şey konmalı.
4. **Ülke seçmeli üretim** — veride 186 ülke var; her ülke için ayrı CSV + sitede seçici.
5. **Talkgroup listesi** (Brandmeister) — D890UV "Talk Groups" CSV'si, deponun eksik ikinci yarısı.

## Ortam notları

- `pytest` ve `unidecode` bu makinede kurulu.
- Depoda git kimliği yerel ayarlı (bkz. CLAUDE.md); global `.gitconfig` yok, olmamalı.
- Bash aracıyla heredoc'a Türkçe metin yazdırma kesme işareti yüzünden bozuluyor
  (`ID'sinin` gibi) — dosya yazarken Write aracını kullan.
