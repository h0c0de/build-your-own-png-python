# CATATAN — Build 27: PNG Decoder + Encoder

Satu halaman per irisan: konsep inti + temuan.
Panduan: Spesifikasi PNG (W3C/ISO 15948).
Baterai: PngSuite (lunapaint/pngsuite @8cd768dd,
175 berkas). Wasit: Pillow 13.0.0.

## Irisan 1 — Kerangka chunk + CRC + IHDR (177)

**Konsep.** Berkas PNG adalah tanda tangan 8
byte diikuti rantai chunk: panjang, tipe 4
huruf, data, CRC-32 atas tipe+data. Nama berkas
PngSuite sendiri adalah spek mini — kode huruf
tipe warna + dua digit kedalaman + awalan
interlace — jadi header 161 berkas sah bisa
diverifikasi silang terhadap namanya sendiri.

**Temuan.** Semua 14 berkas korup resmi (x*)
ditolak, tetapi penolakan pertama datang sebagai
pengecualian build 23 (`GalatDeflate`), bukan
`GalatPNG` — dekoder yang membungkus mesin
orang (bahkan mesin sendiri dari build lain)
wajib menerjemahkan galat di perbatasannya,
kalau tidak API-nya bocor dua bahasa.

## Irisan 2 — Unfilter + piksel (138)

**Konsep.** Setiap baris pindai diawali satu
byte filter; rekonstruksinya kausal: Sub memakai
byte yang *baru direkonstruksi* di baris yang
sama, Up/Average/Paeth memakai baris sebelumnya
yang sudah utuh. Sesudah itu contoh dikemas
MSB-dulu untuk kedalaman <8 dan big-endian
untuk 16 bit.

**Temuan.** Dua quirk wasit, keduanya di sisi
Pillow, keduanya kubuktikan dari contoh mentah:
(1) grayscale 16-bit dimuat Pillow sebagai
I;16 dan `convert('RGBA')` *menjepit* nilai ke
255 alih-alih menggeser — ekspektasi dibangun
dari contoh mentah Pillow digeser >>8;
(2) tRNS grayscale <8-bit: Pillow menyimpan
piksel terskala (×17) tetapi nilai transparansi
dalam satuan mentah spek, jadi tidak ada piksel
yang pernah cocok dan alfa selalu 255 — padahal
spek membandingkan contoh mentah. Ekspektasi
untuk dua kelas itu dibangun dari data Pillow +
aturan spek, dan dicatat terbuka di harness.
Sesudah itu 138/138 identik, termasuk 16-bit
RGB/RGBA yang memang direndahkan Pillow dengan
byte tinggi seperti build ini.

## Irisan 3 — Adam7 + sapuan penuh (322)

**Konsep.** Interlace Adam7 menyebar piksel ke
tujuh lintasan berlangkah (8,8), (8,8), (4,8),
(4,4), (2,4), (2,2), (1,2) — tiap lintasan
adalah gambar kecilnya sendiri yang difilter
dari nol, bukan kelanjutan filter gambar utuh.

**Temuan.** Sapuan penuh menutup semua kategori
sekaligus: 161/161 berkas sah identik Pillow,
dan setiap aliran IDAT di suite menghasilkan
byte identik di inflate build 23 dan zlib
stdlib — jembatan antar-build terkunci dua
arah oleh data resmi, bukan oleh klaim.

## Irisan 4 — Enkoder (322)

**Konsep.** Menulis adalah arah sebaliknya:
pilih per baris satu dari lima filter dengan
heuristik jumlah-nilai-absolut (byte hasil
ditafsir signed), kompres aliran mentahnya
dengan kompresor build 23, bungkus jadi chunk
dengan CRC build 23 juga.

**Temuan.** Round-trip dua arah bersih pada
seluruh suite: Pillow membaca PNG keluaran
build ini piksel-identik, dan build ini membaca
balik keluarannya sendiri identik. Enkoder yang
hanya menulis filter 0 akan tetap lolos uji
seperti ini — yang membuat irisan ini jujur
adalah bahwa IDAT-nya datang dari kompresor
yang sudah terbukti di build 23, dan pembaca
lawannya adalah Pillow, bukan kode sendiri.
