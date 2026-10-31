"""İndirme sayfasındaki karşılaştırma görsellerini üretir: aynı çağrı, iki telsiz ekranı.

Solda radioid.net user.csv olduğu gibi CPS'e alınmış telsiz, sağda bu deponun ürettiği
liste. Ekran düzeni operatörün D890UV fotoğraflarından (2026-11-01):
- Ham dosyada sütunlar bir kayıyor: konum satırları soyad / şehir / bölge oluyor, ülke
  hiç görünmüyor; isimden sonraki satır (soyad) tek isimli kişilerde boş.
- Telsiz ASCII dışı her harfi UTF-8 bayt sayısı kadar "?" gösteriyor. Fotoğrafla
  doğrulanan: "İzmit" -> "??zmit"; diğer yazılar için aynı kural varsayıldı.
- Telsiz uzun satırı keser ve ".." koyar ("Somma Vesuvi..", "North Caroli..").
Sağ taraf generator.py'nin kendi fonksiyonlarıyla hesaplanır; kod değişince yeniden çalıştır.

Anonimleştirme: examples.json'da Radio ID'nin son hanelerinin ve çağrı işaretinin ilk üç
karakterden sonrasının yalnızca uzunluğu var, kendisi yok. Adlar açık.

Çalıştırma (Pillow ve Microsoft Edge gerekir; CI'da çalışmaz, görseller depoya girer):
    python -X utf8 tools/compare/render.py
Çıktı: assets/compare/01.webp ... 20.webp
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape as E

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import generator as g  # noqa: E402

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = ROOT / "assets" / "compare"

LCD = "Verdana, DejaVu Sans, sans-serif"
VB = ImageFont.truetype(r"C:\Windows\Fonts\verdanab.ttf", 100)
VR = ImageFont.truetype(r"C:\Windows\Fonts\verdana.ttf", 100)

W, H = 400, 300                       # ekranın etkin alanı (D890UV ~4:3)
U = H / 262                           # fotoğraftan ölçülen düzen 262 birim
FS, NS, ROW = 19 * U, 26 * U, 24 * U  # normal satır, ad satırı, vurgulu başlık
Y_HEAD, Y_ID, Y_NAME, Y_LOC, Y_TG, Y_SEP, Y_KEYS = 26, 76, 106, (133, 159, 185), 213, 220, 246
BAND = "#d63a2f"                      # sansür bandı: koyu ekranda belli olsun diye kırmızı
TEXT = "#e8ecff"
PW, PH = 1000, 420                    # tüm görsel


def width(s, size, bold=True):
    return (VB if bold else VR).getlength(s) * size / 100


LOC_MAX = width("Somma Vesuvi..", FS)        # fotoğrafta konum satırı burada kesiliyor
NAME_MAX = W - 40


def cut(s, size, max_w, bold=True):
    """Telsiz gibi: sığmayan satırın sonuna '..' koy."""
    if width(s, size, bold) <= max_w:
        return s
    while s and width(s + "..", size, bold) > max_w:
        s = s[:-1]
    return s.rstrip() + ".."


def radio_raw(s):
    return "".join(c if ord(c) < 128 else "?" * len(c.encode("utf-8")) for c in s)


def text(x, y, s, size=FS, bold=True, fill=TEXT, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{LCD}" font-weight="{700 if bold else 400}" '
            f'font-size="{size:.2f}" fill="{fill}" text-anchor="{anchor}" xml:space="preserve">{E(s)}</text>')


def id_line(x, y, ex):
    """'2500123<-R4HAB' satırı; gizli kısım yalnızca uzunluk olarak biliniyor."""
    id_hidden = "8" * ex["id_hidden"]
    cs_hidden = "W" * ex["cs_hidden"]
    out = [text(x, y, ex["id_open"]), text(x + width(ex["id_open"] + id_hidden, FS), y, "<-" + ex["cs_open"])]
    top, bh = y - FS * 0.84, FS * 1.0
    spans = ((ex["id_open"], id_hidden),
             (ex["id_open"] + id_hidden + "<-" + ex["cs_open"], cs_hidden))
    for before, hidden in spans:
        if hidden:
            out.append(f'<rect x="{x + width(before, FS) - 1:.1f}" y="{top:.1f}" '
                       f'width="{width(hidden, FS) + 2:.1f}" height="{bh:.1f}" rx="2" fill="{BAND}"/>')
    return "".join(out)


def status_bar(ox, oy):
    a = [f'<rect x="{ox+8+i*5}" y="{oy+19-h}" width="3" height="{h}" fill="{TEXT}"/>'
         for i, h in enumerate((5, 8, 11, 14))]
    a.append(f'<circle cx="{ox+70}" cy="{oy+12}" r="7" fill="#c8526a"/>')
    a.append(f'<path d="M{ox+82} {oy+6} l10 12 M{ox+92} {oy+6} l-10 12" stroke="#7fa7d8" stroke-width="2.5"/>')
    a.append(f'<rect x="{ox+W-70}" y="{oy+5}" width="30" height="15" rx="2" fill="none" stroke="#3ec46d" stroke-width="2"/>')
    a += [f'<rect x="{ox+W-67+i*9}" y="{oy+8}" width="7" height="9" fill="#3ec46d"/>' for i in range(3)]
    a.append(f'<path d="M{ox+W-28} {oy+5} v15 M{ox+W-34} {oy+5} l6 7 l6 -7" stroke="#cfd6ef" stroke-width="2" fill="none"/>')
    return "".join(a)


def call_icon(cx, cy):
    """Grup çağrısı simgesi: mavi bulut üstünde iki kişi, sağ altta geri ok."""
    return (f'<ellipse cx="{cx}" cy="{cy+10}" rx="30" ry="15" fill="#2f86d6"/>'
            f'<circle cx="{cx-9}" cy="{cy-10}" r="7" fill="#e9d9b8"/><circle cx="{cx+9}" cy="{cy-12}" r="7" fill="#e9d9b8"/>'
            f'<rect x="{cx-17}" y="{cy-3}" width="16" height="14" rx="5" fill="#d9e3f0"/>'
            f'<rect x="{cx+1}" y="{cy-5}" width="16" height="16" rx="5" fill="#d9e3f0"/>'
            f'<circle cx="{cx+22}" cy="{cy+16}" r="10" fill="#1f63b5" stroke="#fff" stroke-width="1.5"/>'
            f'<path d="M{cx+27} {cy+16} h-10 m4 -4 l-4 4 l4 4" stroke="#fff" stroke-width="2" fill="none"/>')


def screen(ox, oy, ex, name, places):
    def Y(v):
        return oy + v * U

    a = [f'<rect x="{ox-14}" y="{oy-14}" width="{W+28}" height="{H+28}" rx="20" fill="#050608" stroke="#2b2e34" stroke-width="2"/>',
         f'<rect x="{ox}" y="{oy}" width="{W}" height="{H}" fill="url(#lcd)"/>',
         status_bar(ox, oy),
         f'<rect x="{ox+4}" y="{Y(Y_HEAD):.1f}" width="{W-8}" height="{ROW:.1f}" fill="#2649d6"/>',
         text(ox + 8, Y(Y_HEAD) + ROW * 0.80, "(A)TG: TG91 World-w..", fill="#ffffff"),
         id_line(ox + 18, Y(Y_ID), ex),
         text(ox + 18, Y(Y_NAME), cut(name, NS, NAME_MAX, bold=False), NS, bold=False)]
    for base, s in zip(Y_LOC, places):
        a.append(text(ox + 18, Y(base), cut(s, FS, LOC_MAX)))
    a.append(call_icon(ox + W - 58, Y(Y_LOC[1]) - 4))
    a.append(text(ox + 18, Y(Y_TG), "TG91 World-wide"))
    a.append(f'<rect x="{ox+10}" y="{Y(Y_SEP):.1f}" width="{W-20}" height="2" fill="#cfd6ef"/>')
    for s, x, anchor in (("Menu", ox + 12, "start"), ("Zone\u21d5", ox + W / 2, "middle"), ("List", ox + W - 10, "end")):
        a.append(text(x, Y(Y_KEYS), s, fill="#f2f4ff", anchor=anchor))
    return "".join(a)


def svg(ex):
    raw_name = radio_raw(ex["first"])
    raw_places = ["", radio_raw(ex["city"]), radio_raw(ex["state"])]
    our_name = g.clean_name(ex["first"], "")
    our_places = [g.clean_place(ex["city"]), g.clean_place(ex["state"]), g.transliterate_field(ex["country"])]
    lx, rx, sy = 50, 550, 82
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">',
             '<defs><linearGradient id="lcd" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="#121a4a"/><stop offset="1" stop-color="#070a22"/></linearGradient></defs>',
             f'<rect width="{PW}" height="{PH}" fill="#f6f3ea"/>']
    for x, label, colour in ((lx, "RADIOID.NET USER.CSV", "#635c50"), (rx, "CONTACTS.APRSAGENT.COM", "#b0413e")):
        parts.append(f'<text x="{x-14}" y="48" font-family="Consolas, monospace" font-size="18" '
                     f'font-weight="700" letter-spacing="2" fill="{colour}">{label}</text>')
    parts.append(screen(lx, sy, ex, raw_name, raw_places))
    parts.append(screen(rx, sy, ex, our_name, our_places))
    parts.append("</svg>")
    return "".join(parts)


def main():
    examples = json.loads((Path(__file__).parent / "examples.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for i, ex in enumerate(examples, 1):
            s, png = Path(tmp) / f"{i:02}.svg", Path(tmp) / f"{i:02}.png"
            s.write_text(svg(ex), encoding="utf-8")
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", "--allow-file-access-from-files",
                            f"--window-size={PW},{PH}", f"--screenshot={png}", s.as_uri()],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            Image.open(png).convert("RGB").save(OUT / f"{i:02}.webp", "WEBP", quality=86, method=6)
            print(f"{i:02}.webp  {g.clean_name(ex['first'], '')}")


if __name__ == "__main__":
    main()
