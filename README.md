# Build Your Own — PNG Decoder + Encoder

Decoder **PNG** lengkap dalam Python murni,
dibangun dari **Spesifikasi PNG** (W3C/ISO) dan
dibuktikan dengan baterai konformansi resmi
formatnya: **PngSuite** — seluruh 161 berkas sah
terdekode **identik piksel-demi-piksel** dengan
Pillow, dan ke-14 berkas korup resmi ditolak.

Jembatan serinya nyata: aliran IDAT PNG adalah
format zlib, jadi ia didekompresi *dan*
dikompresi memakai **kode build 23** (DEFLATE/
zlib) yang disalin utuh ke repo ini — dan setiap
aliran IDAT di suite dibuktikan menghasilkan
byte yang sama di inflate build 23 dan di zlib
pustaka standar.

## Isi

| Berkas | Isi |
| --- | --- |
| `pngku.py` | Decoder + encoder-nya: chunk/CRC, semua tipe warna & kedalaman 1–16 bit, 5 filter, Adam7, PLTE/tRNS |
| `bit.py` `huffman.py` `deflate.py` `bungkus.py` `pampat.py` | Kode build 23 (vendored) — mesin zlib di balik IDAT |
| `uji_bersama.py` | Wasit piksel Pillow (+ dua quirk wasit yang terdokumentasi) |
| `uji_irisan1.py` … `uji_irisan4.py` | Uji per irisan (perlu Pillow + PngSuite di `../png-ref`) |

## Memakai

```python
from pngku import dekode, enkode, Gambar

g = dekode(open("gambar.png", "rb").read())
print(g.lebar, g.tinggi, g.piksel_di(0, 0))  # RGBA

png_baru = enkode(g)   # tipe 6, filter dipilih
                       # per baris, IDAT dari
                       # kompresor build 23
```

## Tiga hal yang menentukan

1. **Filter bekerja pada byte, bukan piksel** —
   dan "kiri" berarti *bpp byte* ke kiri (byte
   per piksel dibulatkan ke atas, minimal 1).
   Paeth tanpa byte kiri/atas-kiri yang benar
   menggeser seluruh gambar sesudah baris
   pertama.

2. **Adam7 adalah tujuh gambar kecil**, masing-
   masing difilter sendiri dari baris nolnya.
   Piksel lintasan disebar ke koordinat
   (x0 + i·dx, y0 + j·dy); ukuran lintasan yang
   nol piksel dilewati seluruhnya.

3. **Kedalaman 16 bit direndahkan dengan byte
   tingginya**, dan nilai tRNS dibandingkan ke
   contoh *mentah* sebelum penskalaan — dua
   tempat di mana wasit populer (Pillow) sendiri
   menyimpang; lihat CATATAN irisan 2.

## Di luar lingkup

Chunk tampilan (gAMA, cHRM, iCCP) dilewati tanpa
diterapkan — keluarannya data piksel mentah
sesuai spek, bukan hasil koreksi warna. APNG
tidak didukung.

## Lisensi

Kode: MIT. Spesifikasi PNG © W3C; PngSuite
domain publik (Willem van Schaik); Pillow hanya
wasit uji, tidak disertakan.
