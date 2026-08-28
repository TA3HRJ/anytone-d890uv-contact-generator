# anytone-contact-generator

Türkçe konuş. Kullanıcı Türkçe çalışıyor.

AnyTone D890UV (ve D878UV) için [radioid.net](https://radioid.net) dökümlerinden ekran karakter
sınırına uygun DMR ve NXDN kişi listesi CSV'leri üretir. Depo: `TA3HRJ/anytone-d890uv-contact-generator`

## Çalıştırma

```bash
pip install -r requirements.txt    # unidecode
python generator.py
```

Script radioid.net'ten güncel DMR ve NXDN dökümlerini indirir, isimleri harf çevirisiyle işler ve
`output/` altına 6 CSV üretir: her protokol için Türkiye / Avrupa / Dünya.

## Neyin neden böyle olduğu

- **ASCII harf çevirisi zorunlu** — telsizin ekranı Türkçe ÇİĞÖŞÜ, Almanca äöü, Kiril veya CJK
  gösteremiyor. `unidecode` ile en yakın ASCII karşılığa çevriliyor.
- **16 karakter kesme sınırı** — kelimeyi ortadan bölmeden kesiyor; bu davranışı değiştirirken
  ekranda okunabilirliği bozmamaya dikkat et.
- **Çıktı formatı D890UV CPS'in import/export formatıyla birebir eşleşmek zorunda.** Sütun
  sırası veya başlık değişirse CPS dosyayı reddeder.

## Notlar

- `output/` üretilen dosyalar içindir, kaynak değil.
- Bu depo yalnızca CSV üreticisidir. ESP32-S3 tabanlı dahili WiFi / hotspot'suz Brandmeister
  donanım fikri ayrı bir iştir ve henüz hiçbir klasörde kodu yoktur.

## Oturum sonu

Anlamlı bir iş yaptıysan — bir karar verildi, bir şey kırılıp düzeldi, bir varsayım ölçüldü —
bitirmeden önce `docs/HANDOFF.md`'yi güncelle: nerede kalındı, ne açık kaldı, hangi tuzağa
düşüldü ve neden. Dosya yoksa oluştur.

Sohbet geçmişi kalıcı değildir. Repoda yazılı olmayan her şey oturumla birlikte gider.
