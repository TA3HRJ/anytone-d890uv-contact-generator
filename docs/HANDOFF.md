# HANDOFF

Son güncelleme: 2026-10-10

## Durum

Üretim çalışıyor ve sağlıklı. Her gün radioid.net'ten altı CSV üretilip
https://contacts.aprsagent.com adresine (GitHub Pages) yayınlanıyor (kesin saat yok, bkz. 8. iş);
iş başarısız olursa `uretim-hatasi` etiketiyle issue açılıyor. Bozuk indirme mevcut çıktının
üzerine yazamıyor. 109 test `generator.py`'den önce koşuyor.

Açık listede **yapılmayı bekleyen iş yok** — kalan iki madde de bilinçli kararla beklemede
(aşağıda gerekçeleriyle). Yeni bir yön belirlenmeden buradan devam edilecek bir şey yok.

**8. ve 9. işin üretimdeki sonucu (2026-10-10'da ölçüldü):** 2026-09-25'ten 2026-10-09'a
15 zamanlanmış koşunun hepsi yeşil, hepsi yeni kodla (`1479fb8`), açık issue yok. 2026-10-09
yayını: DMR 314.668 / 115.186 / 8.518, NXDN 18.035 / 6.245 / 667.
**Cron kaydırması gecikmeyi azaltmadı:** `23 5` ile koşular 09:56-12:22 UTC arasında başladı
(eski `0 6` ile 10:20-12:20). GitHub zamanlanmış işleri 4,5-7 saat erteliyor; dakika seçimi
fark etmiyor. Sayfa kesin saat vaat etmediği için sorun değil, yeniden denemeye gerek yok.

Bu makinede `gh` yok; durum GitHub REST API'sinden anonim okunuyor:
`Invoke-RestMethod https://api.github.com/repos/TA3HRJ/anytone-d890uv-contact-generator/actions/runs?per_page=10`.

**Elle yayın (push yayın tetiklemez):** kullanıcının Chrome'unda GitHub oturumu açık;
Claude in Chrome ile Actions → Generate Contact Lists → Run workflow'a basılabiliyor.
Desktop uygulamasının kendi tarayıcı panelinde oturum **yok** — "erişim yok" sanıp kullanıcıya
bırakma, önce Chrome'u dene.

## Nerede kalındı

Dokuz iş bitti, hepsi gerçek veriyle doğrulandı (8. iş 9. işte ölçüldü):

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

**Bu çözüm 7. işte geçersiz kaldı** — sürüm anahtarı ve iki `sed` tamamen kaldırıldı, tarih
`stats.json`'a taşındı. Burası tarihi kayıt olarak duruyor; kodda `{{VERSION}}` aramayın.

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

### 8. Denetim (2026-09-24): kutulama, zamanlama, izinler

Program, GitHub ve site baştan denetlendi. Son 20 Actions çalıştırması yeşil, açık issue
yok, 2026-09-24 logu: DMR 313.749 / Avrupa 114.756 / Türkiye 8.465, NXDN 17.842 /
6.147 / 659; ülke boşluğu raporunda yalnızca bilinen 5 yanlış kayıt (US 3, Canada 2).

**Kutulama hatası (5. işteki `normalize_case`):** karar parça bazında veriliyordu, yani
doğru yazılmış bir alanın içindeki tek biçimli parça da `title()` yiyordu:
`Frankfurt am Main` -> `Frankfurt Am Main`, `Jan van der Berg` -> `Jan Van Der Berg`,
`Washington DC` -> `Washington Dc`. 5. iş karışık kutulu *parçaları* korumuştu ama küçük
harfli ekleri ve büyük harfli kısaltmaları hesaba katmamıştı. Artık karar **alan bazında**:
alanın tüm harfleri tek biçimdeyse düzeltiliyor, değilse alan olduğu gibi kalıyor.
DMR'de ad ve soyad **ayrı** kutulanıyor — yoksa `Jean` + `DUPONT` birleşince karışık
alan olur ve soyad düzelmezdi.

Bu oturumda ağ olmadığı için ölçülemedi; ölçüm ve çıkan yan etkinin düzeltmesi 9. işte.

**"Bilinen sınır" ölçüldü, sorun değil:** tek başına kısa eyalet alanı (`NSW` -> `Nsw`
korkusu) veride yok. 3 harf ve altındaki bütün STATE değerleri zaten tam ad (`Zug`, `Ica`,
`Goa`; DMR'de toplam 37). `NSW`/`SP` yalnızca karışık alanların *içinde* geçiyor, orada
korunuyor.

**Zamanlama:** cron `0 6` idi ama zamanlanmış çalıştırmalar 10:20-12:20 UTC arasında
başlıyordu (GitHub yük altında erteliyor, 17 gün boyunca her gün). Site ve README "06:00 UTC"
vaat ediyordu; artık "günde bir kez, son çalıştırma altta" diyorlar. Cron saat başından
`23 5`'e kaydırıldı — gecikmeyi azaltıp azaltmadığı bir hafta izlenmeli, garanti değil.

**Küçükler:** workflow izni `contents: write` -> `read` (iş depoya yazmıyor). İndirme
`utf-8-sig` ile çözülüyor (BOM gelirse her satır geçersiz sayılıyordu). `transliterate_field`
boşluğu sadeleştiriyor (unidecode CJK sonrası boşluk bırakıyor, alan içi satır sonu CSV'de
çok satırlı hücre üretirdi).

### 9. Kutulama gerçek veriyle ölçüldü, karışık alandaki unutulmuş küçük harf düzeltildi

Bu makinede Python yoktu; `winget` ile Python 3.13 (kullanıcı kapsamı) kuruldu, depo
içinde `.venv` açıldı (kendi `.gitignore`'u var, depoya girmiyor). Ölçüm 2026-09-24
verisiyle, eski (`56958de~1`) ve yeni `generator.py` **aynı indirilmiş dökümün** üzerinde
koşturularak yapıldı — eski kural üretimdeki 13.037'yi birebir verdi, yani veri aynıydı.

**8. işin etkisi (alan bazında karar):** DMR'de ~9.300 şehir/bölge alanı düzeldi
(`Rio De Janeiro` -> `Rio de Janeiro` 110+676, `Reg.Metr. De Santiago` -> `... de ...` 1.057,
`Dki Jakarta` -> `DKI Jakarta` 257, `Frankfurt Am Main` 23). İsimde 828 alan değişti,
çoğu kısaltmanın korunması (`Snohomish ACS`, `Scouts WA`).

**Ama bir gerileme getirmişti:** karışık kutulu alanın içinde gerçekten unutulmuş küçük harf
artık düzelmiyordu — `Saint cloud`, `Ernest southwood`, `Jean pierre`, `Radio club`,
`Sao paulo`. Eski parça bazlı kural bunları düzeltiyordu.

**Karışık alanlardaki parçalar sınıflara ayrılıp sayıldı (DMR):**

| Sınıf | Adet | İçerik | Karar |
|---|---|---|---|
| küçük, ≤3 harf | 7.854 | neredeyse tamamı bağlaç: de, do, del, am, nad, og, sur | dokunma |
| küçük, ≥4 harf | 1.964 | çoğu unutulmuş: city, club, trent, island, pierre | **düzelt** |
| BÜYÜK, 2-3 harf | 1.408 | kısaltma: DKI, ARC, NSW, SP, RC | dokunma |
| BÜYÜK, ≥4 harf | 445 | yarı yarıya: ARES, NZART, DARC, IEEE / KONYA, TOLEDO | dokunma |

**Yeni kural (`is_lowercase_word`):** karışık alanda yalnızca 4+ harfli, tamamen küçük,
yalnız harften oluşan parçalar `title()` alıyor. 4+ harfli bağlaçlar için küçük bir istisna
listesi var (`LOWERCASE_CONNECTORS`: upon, under, super, della/delle/degli…) —
`Newcastle upon Tyne` 59 kez geçiyor. Tek biçimli alanların davranışı değişmedi.

**Ölçülen sonuç:** yeni kural 8. işin üzerine ~1.700 alanı daha düzeltiyor (DMR isim 209,
şehir 1.385, bölge 50; NXDN 58). Rastgele örneklemde yanlış düzeltme görülmedi.
`Rewrote N names`: eski 13.037 -> alan bazlı 12.356 -> şimdiki 12.538.

**Kalan, bilerek bırakılan:** karışık alandaki 3 harfli küçük kelimeler (`Castel san
Giorgio`, `Paris Sv7 lpk`) ve büyük harfle yazılmış yer adları (`PUGET sur Argens`) —
ikisini de bağlaçtan/kısaltmadan ayırt etmek elle tutulan bir liste gerektirir.

### 10. Sayfa aprsagent.com ailesinin temasına geçti (2026-10-10)

Site artık `*.aprsagent.com` ailesinin parçası. Ortak standart depo dışında:
`C:\Claude Projects\_shared\aprsagent-site-standardi\` (README, `family.css`, `snippets.html`).
Ana sayfanın görünümü değişirse önce orası, sonra bu depo güncellenir.

- `family.css` ve `assets/aprsagent-mark.svg` standarttan **kopyalandı**, uzaktan bağlanmıyor.
  Sayfaya özgü stil (tablo, adım listesi) `index.html` içinde ve yalnızca family.css
  değişkenlerini kullanıyor.
- Başlık çubuğunda ana sayfaya geri bağlantı, altta "Ham radio tools" satırı,
  `#legal` bölümü (ticari markalar + sorumluluk reddi + radioid.net/kişisel veri maddesi),
  README'de "Trademarks and disclaimer". AnyTone/D890UV için ® konmadı: sahibinin kendi
  belgesinde ® kanıtı yok, genel "olabilir" cümlesi kapsıyor. İlk sürümde site tek dilli
  (İngilizce) bırakılmıştı; 11. işte EN/TR yapıldı.
- Workflow artık `family.css` ve `assets/`'i de `_site`'a kopyalıyor. **Tuzak:** sayfaya yeni
  yerel dosya eklenip workflow'a eklenmezse site temasız yayınlanır; bunu
  `test_workflow_publishes_every_local_file_the_page_loads` yakalıyor (kopyalama satırı
  silinerek denendi, test kaldı).
- **Standarttaki hata:** `snippets.html` §3 `<div class="wrap legal">` veriyor. `.legal`'in
  `max-width:78ch` değeri `.wrap`'ın genişliğini ezip `margin:auto` ile kutuyu ortaya
  kaydırıyor. Burada önce `<div class="wrap"><div class="legal">` ile çözüldü, sonra
  standardın kendisi düzeltildi (sürüm 1.1): `max-width` `.legal`'den çocuklarına
  (`.legal>*`) taşındı, iki kalıp da doğru hizalanıyor. Bu depodaki `family.css` 1.1'e
  eşitlendi. turkey-repeaters'a yalnızca bu düzeltme yamalandı (gerekçesi orada HANDOFF'ta).
- **Standart hareketli:** başka oturumlar 1.2 (`.bar` → `.fam-row`, yeni `--series-*`) ve
  1.3 (tema düğmesi `.thm`, QRZ bağlantısı) çıkardı ve bu depoyu da 1.3'e eşitledi
  (`2a15520`, `a2cc1c2`). Sayfa artık `wrap fam-row` kullanıyor. Standart başka oturumlarca
  da değiştiriliyor; buraya kopyalamadan önce `git log` ve standardın README §6'sına bak.
- Masaüstü (1280) ve 375px'te yerel önizlemeyle bakıldı: yatay kaydırma yok, şerit ile
  başlık çubuğu çakışmıyor, aprsagent.com ile yan yana aynı aile görünüyor.
- **Yayında (2026-10-09 22:03 UTC, elle tetiklenen koşu #104, `1ce8506`):** canlıda
  `family.css`, logo, `stats.json` ve CSV'ler 200; sayfa yeni temada, sayılar ve tarih geliyor.

### 11. Sayfa iki dilli (TR/EN), varsayılan TR (2026-10-10)

Diğer aile sitelerinde olan EN/TR anahtarı burada yoktu; 10. işte talimattaki "tek dilliyse
sitenin dilinde" cümlesi "İngilizce kalsın" diye okunmuş ve kullanıcıya sorulmamıştı.
Kullanıcı istedi, varsayılanı **her zaman TR** seçti (tarayıcı diline bakılmıyor).

- HTML'in kendisi Türkçe; `<head>`'deki küçük betik `localStorage["lang"]`'i okuyup
  `<html lang>`'i ilk boyamadan önce koyuyor. Sözlük (`STRINGS.tr` / `STRINGS.en`) sayfa
  sonunda; `data-i` öğelerin içeriğini, `data-i-aria` indirme düğmelerinin `aria-label`'ını
  değiştiriyor. Anahtar adı `lang`, coax ve repeaters ile aynı.
- Sayılar seçili dile göre biçimleniyor (TR `8.518`, EN `8,518`); eskiden tarayıcı diline bağlıydı.
- CPS menü adları (`DMR > Digital Contact List`, `Tool > Import`) iki dilde de İngilizce —
  CPS'in arayüzü öyle.
- `test_every_translated_element_has_both_languages`: sayfadaki her anahtarın iki sözlükte
  de olduğunu ve sözlüklerin eşit olduğunu denetliyor (bir EN anahtarı silinerek denendi,
  test kaldı ve eksik anahtarı adıyla gösterdi).
- Yerelde doğrulandı: boş tarayıcıda TR açılıyor, EN'ye geçiş ve yenilemeden sonra hatırlama
  çalışıyor, 375px'te tema + EN/TR + GitHub sığıyor, yatay kaydırma yok.

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
