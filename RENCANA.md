# RENCANA — Build 27: PNG Decoder (+ Encoder)

Sumber: **Spesifikasi PNG** (W3C Recommendation /
ISO/IEC 15948) sebagai panduan, **PngSuite**
(suite uji resmi Willem van Schaik, domain publik)
sebagai baterai konformansi, dan **Pillow**
sebagai wasit diferensial piksel — pola yang sama
dengan build 24: speknya yang dibaca, suite
resminya yang menghakimi.

Jembatan seri: aliran IDAT PNG adalah format
zlib — didekompresi (dan untuk enkoder,
dikompresi) memakai **kode build 23** (bit.py,
huffman.py, deflate.py, bungkus.py, pampat.py)
yang disalin utuh (vendored) ke repo ini.
Diferensialnya mengunci dua arah: inflate build
23 vs zlib stdlib pada setiap aliran IDAT suite.

## Lingkup

MASUK:
- Dekoder penuh: signature, chunk + CRC-32
  (build 23), IHDR semua tipe warna (0 gray,
  2 RGB, 3 palet, 4 gray+alpha, 6 RGBA) dan
  kedalaman bit 1/2/4/8/16, kelima filter
  (None/Sub/Up/Average/Paeth), interlace Adam7,
  PLTE + tRNS, banyak IDAT, penolakan berkas
  korup (kategori x* PngSuite + CRC rusak).
- Keluaran piksel ternormalisasi RGBA8 +
  akses piksel mentah per tipe asli.
- Enkoder: tulis PNG dari piksel RGBA8 (pilih
  filter per baris heuristik, IDAT dari
  kompresor build 23), round-trip dua arah
  melawan Pillow.

DILUAR (tercatat):
- Chunk tampilan (gAMA/cHRM/iCCP/dll.) dibaca
  lewati, tidak diterapkan — piksel adalah
  data mentah sesuai spek, bukan hasil koreksi
  warna. APNG di luar lingkup.

## Irisan

- [x] Irisan 1 — Kerangka chunk + CRC + IHDR:
  parse semua berkas suite, header terverifikasi
  silang nama berkas PngSuite (kode nama = tipe
  warna/kedalaman/interlace), korup ditolak.
- [x] Irisan 2 — IDAT + unfilter + piksel
  non-interlace: diferensial piksel vs Pillow
  untuk basn*/f*/s*/t*/z*/bg*/g*/c*.
- [x] Irisan 3 — Adam7 + sapuan penuh: basi*/oi*
  + seluruh suite yang terdekode; x* semua
  ditolak; IDAT build 23 == zlib stdlib.
- [x] Irisan 4 — Enkoder + final: round-trip
  Pillow membaca keluaran kita byte-piksel sama;
  kita membaca keluaran Pillow sama.

## Pagar selesai

- [x] `uji_irisan1.py` … `uji_irisan4.py` hijau.
- [x] `CATATAN.md` satu halaman per irisan.
- [ ] Repo GitHub publik
  `build-your-own-png-python` terbit dan
  terverifikasi (SHA blob lokal == remote, halaman
  publik terbaca).
