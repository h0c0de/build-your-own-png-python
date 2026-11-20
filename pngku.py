"""PNG decoder + encoder menurut Spesifikasi PNG
(W3C / ISO/IEC 15948).

Aliran IDAT adalah format zlib: didekompresi dan
dikompresi memakai kode build 23 seri ini
(bit/huffman/deflate/bungkus/pampat, vendored).

Keluaran dekoder: piksel ternormalisasi RGBA8
(bytes, baris demi baris) + metadata IHDR.
Chunk tampilan (gAMA dll.) dilewati, tidak
diterapkan — piksel adalah data mentah spek.
"""

import struct

from bit import GalatDeflate
from bungkus import crc32
from pampat import dekompres, kompres

TANDA = b"\x89PNG\r\n\x1a\n"


class GalatPNG(Exception):
    pass


# tipe warna -> jumlah kanal
_KANAL = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
# tipe warna -> kedalaman bit yang sah
_KEDALAMAN_SAH = {0: (1, 2, 4, 8, 16), 2: (8, 16),
                  3: (1, 2, 4, 8), 4: (8, 16),
                  6: (8, 16)}


class Gambar:
    def __init__(self, lebar, tinggi, kedalaman,
                 tipe, interlace, piksel_rgba,
                 palet=None, trns=None):
        self.lebar = lebar
        self.tinggi = tinggi
        self.kedalaman = kedalaman
        self.tipe = tipe
        self.interlace = interlace
        # bytes RGBA8, panjang lebar*tinggi*4
        self.piksel = piksel_rgba
        self.palet = palet
        self.trns = trns

    def piksel_di(self, x, y):
        i = (y * self.lebar + x) * 4
        return tuple(self.piksel[i:i + 4])


def _baca_chunk(data, pos):
    if pos + 8 > len(data):
        raise GalatPNG("chunk terpotong")
    (panjang,) = struct.unpack_from(">I", data, pos)
    tipe = data[pos + 4:pos + 8]
    if pos + 12 + panjang > len(data):
        raise GalatPNG("data chunk terpotong")
    isi = data[pos + 8:pos + 8 + panjang]
    (crc_baca,) = struct.unpack_from(
        ">I", data, pos + 8 + panjang)
    if crc32(tipe + isi) != crc_baca:
        raise GalatPNG("CRC chunk %s rusak"
                       % tipe.decode("latin1"))
    return tipe, isi, pos + 12 + panjang


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _tanpa_filter(mentah, lebar_byte, bpp):
    """mentah: baris-baris diawali byte filter.
    Kembalikan daftar bytearray per baris."""
    baris = []
    prev = bytearray(lebar_byte)
    pos = 0
    while pos < len(mentah):
        f = mentah[pos]
        pos += 1
        cur = bytearray(mentah[pos:pos + lebar_byte])
        if len(cur) < lebar_byte:
            raise GalatPNG("baris pindai terpotong")
        pos += lebar_byte
        if f == 0:
            pass
        elif f == 1:  # Sub
            for i in range(bpp, lebar_byte):
                cur[i] = (cur[i] + cur[i - bpp]) & 0xFF
        elif f == 2:  # Up
            for i in range(lebar_byte):
                cur[i] = (cur[i] + prev[i]) & 0xFF
        elif f == 3:  # Average
            for i in range(lebar_byte):
                kiri = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] +
                          ((kiri + prev[i]) >> 1)) & 0xFF
        elif f == 4:  # Paeth
            for i in range(lebar_byte):
                kiri = cur[i - bpp] if i >= bpp else 0
                atas_kiri = prev[i - bpp] if i >= bpp \
                    else 0
                cur[i] = (cur[i] + _paeth(
                    kiri, prev[i], atas_kiri)) & 0xFF
        else:
            raise GalatPNG("filter tak dikenal: %d" % f)
        baris.append(cur)
        prev = cur
    return baris


def _contoh_baris(baris, lebar, kanal, kedalaman):
    """Satu baris byte -> daftar contoh (sample)
    integer per kanal, urutan piksel."""
    contoh = []
    if kedalaman == 8:
        contoh = list(baris)
    elif kedalaman == 16:
        for i in range(0, len(baris), 2):
            contoh.append((baris[i] << 8) | baris[i + 1])
    else:  # 1/2/4 bit, kemasan MSB dulu, kanal==1
        per_byte = 8 // kedalaman
        topeng = (1 << kedalaman) - 1
        for b in baris:
            for k in range(per_byte):
                geser = 8 - kedalaman * (k + 1)
                contoh.append((b >> geser) & topeng)
        contoh = contoh[:lebar]
    if len(contoh) < lebar * kanal:
        raise GalatPNG("contoh baris kurang")
    return contoh[:lebar * kanal]


def _ke_rgba8(contoh, lebar, tipe, kedalaman, palet,
              trns):
    """Daftar contoh satu baris -> bytes RGBA8."""
    keluar = bytearray()
    maks = (1 << kedalaman) - 1

    def skala(v):
        if kedalaman == 8:
            return v
        if kedalaman == 16:
            return v >> 8
        return v * 255 // maks

    if tipe == 3:  # palet
        if palet is None:
            raise GalatPNG("PLTE hilang")
        for idx in contoh:
            if idx * 3 + 2 >= len(palet):
                raise GalatPNG("indeks palet lewat")
            r, g, b = palet[idx * 3:idx * 3 + 3]
            a = 255
            if trns is not None and idx < len(trns):
                a = trns[idx]
            keluar += bytes((r, g, b, a))
        return keluar
    kanal = _KANAL[tipe]
    for p in range(lebar):
        s = contoh[p * kanal:(p + 1) * kanal]
        if tipe == 0:
            v = skala(s[0])
            a = 255
            if trns is not None:
                (t,) = struct.unpack(">H", trns[:2])
                if s[0] == t:
                    a = 0
            keluar += bytes((v, v, v, a))
        elif tipe == 2:
            r, g, b = (skala(s[0]), skala(s[1]),
                       skala(s[2]))
            a = 255
            if trns is not None:
                tr, tg, tb = struct.unpack(
                    ">HHH", trns[:6])
                if (s[0], s[1], s[2]) == (tr, tg, tb):
                    a = 0
            keluar += bytes((r, g, b, a))
        elif tipe == 4:
            v = skala(s[0])
            keluar += bytes((v, v, v, skala(s[1])))
        else:  # 6
            keluar += bytes((skala(s[0]), skala(s[1]),
                             skala(s[2]), skala(s[3])))
    return keluar


# (x0, y0, dx, dy) tujuh lintasan Adam7
_ADAM7 = [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8),
          (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2),
          (0, 1, 1, 2)]


def dekode(data):
    """bytes PNG -> Gambar (RGBA8 ternormalisasi)."""
    if data[:8] != TANDA:
        raise GalatPNG("tanda tangan PNG salah")
    pos = 8
    ihdr = None
    palet = None
    trns = None
    idat = bytearray()
    selesai = False
    while pos < len(data):
        tipe, isi, pos = _baca_chunk(data, pos)
        if tipe == b"IHDR":
            if ihdr is not None:
                raise GalatPNG("IHDR ganda")
            (lebar, tinggi, kedalaman, tipe_warna,
             komp, metode_filter, interlace) = \
                struct.unpack(">IIBBBBB", isi)
            if komp != 0 or metode_filter != 0:
                raise GalatPNG("IHDR: metode tak dikenal")
            if tipe_warna not in _KANAL:
                raise GalatPNG("tipe warna tak dikenal")
            if kedalaman not in \
                    _KEDALAMAN_SAH[tipe_warna]:
                raise GalatPNG("kedalaman bit tak sah")
            if lebar == 0 or tinggi == 0:
                raise GalatPNG("dimensi nol")
            ihdr = (lebar, tinggi, kedalaman,
                    tipe_warna, interlace)
        elif tipe == b"PLTE":
            palet = isi
        elif tipe == b"tRNS":
            trns = isi
        elif tipe == b"IDAT":
            idat += isi
        elif tipe == b"IEND":
            selesai = True
            break
    if ihdr is None:
        raise GalatPNG("IHDR hilang")
    if not selesai:
        raise GalatPNG("IEND hilang")
    lebar, tinggi, kedalaman, tipe_warna, interlace = \
        ihdr
    kanal = _KANAL[tipe_warna]
    try:
        mentah = dekompres(bytes(idat))
    except GalatDeflate as e:
        raise GalatPNG("IDAT rusak: %s" % e)
    bit_per_piksel = kanal * kedalaman
    bpp = max(1, (bit_per_piksel + 7) // 8)
    piksel = bytearray(lebar * tinggi * 4)

    def taruh(baris_contoh_rgba, xs, y):
        for i, x in enumerate(xs):
            awal = (y * lebar + x) * 4
            piksel[awal:awal + 4] = \
                baris_contoh_rgba[i * 4:(i + 1) * 4]

    if interlace == 0:
        lebar_byte = (lebar * bit_per_piksel + 7) // 8
        baris = _tanpa_filter(mentah, lebar_byte, bpp)
        if len(baris) < tinggi:
            raise GalatPNG("baris kurang")
        for y in range(tinggi):
            contoh = _contoh_baris(
                baris[y], lebar, kanal, kedalaman)
            taruh(_ke_rgba8(contoh, lebar, tipe_warna,
                            kedalaman, palet, trns),
                  range(lebar), y)
    elif interlace == 1:
        sisa = mentah
        for (x0, y0, dx, dy) in _ADAM7:
            if lebar <= x0 or tinggi <= y0:
                continue
            lw = (lebar - x0 + dx - 1) // dx
            lh = (tinggi - y0 + dy - 1) // dy
            lebar_byte = (lw * bit_per_piksel + 7) // 8
            ambil = lh * (1 + lebar_byte)
            potong, sisa = sisa[:ambil], sisa[ambil:]
            baris = _tanpa_filter(potong, lebar_byte,
                                  bpp)
            for j in range(lh):
                contoh = _contoh_baris(
                    baris[j], lw, kanal, kedalaman)
                taruh(_ke_rgba8(
                    contoh, lw, tipe_warna, kedalaman,
                    palet, trns),
                    range(x0, lebar, dx), y0 + j * dy)
    else:
        raise GalatPNG("interlace tak dikenal")
    return Gambar(lebar, tinggi, kedalaman, tipe_warna,
                  interlace, bytes(piksel), palet, trns)


def _chunk(tipe, isi):
    return (struct.pack(">I", len(isi)) + tipe + isi
            + struct.pack(">I", crc32(tipe + isi)))


def _filter_pilih(baris, prev, bpp):
    """Coba kelima filter, pilih jumlah nilai absolut
    terkecil dari byte hasil yang ditafsir signed —
    heuristik standar enkoder PNG."""
    terbaik = None
    for f in range(5):
        hasil = bytearray(len(baris))
        for i, v in enumerate(baris):
            kiri = baris[i - bpp] if i >= bpp else 0
            atas = prev[i] if prev is not None else 0
            atas_kiri = (prev[i - bpp]
                         if prev is not None
                         and i >= bpp else 0)
            if f == 0:
                ramal = 0
            elif f == 1:
                ramal = kiri
            elif f == 2:
                ramal = atas
            elif f == 3:
                ramal = (kiri + atas) >> 1
            else:
                ramal = _paeth(kiri, atas, atas_kiri)
            hasil[i] = (v - ramal) & 0xFF
        skor = sum(b if b < 128 else 256 - b
                   for b in hasil)
        if terbaik is None or skor < terbaik[0]:
            terbaik = (skor, f, hasil)
    return terbaik[1], terbaik[2]


def enkode(gambar):
    """Gambar (RGBA8) -> bytes PNG tipe 6 kedalaman 8,
    tanpa interlace."""
    lebar, tinggi = gambar.lebar, gambar.tinggi
    mentah = bytearray()
    bpp = 4
    prev = None
    for y in range(tinggi):
        baris = bytearray(
            gambar.piksel[y * lebar * 4:
                          (y + 1) * lebar * 4])
        f, hasil = _filter_pilih(baris, prev, bpp)
        mentah.append(f)
        mentah += hasil
        prev = baris
    ihdr = struct.pack(">IIBBBBB", lebar, tinggi, 8,
                       6, 0, 0, 0)
    return (TANDA + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", kompres(bytes(mentah)))
            + _chunk(b"IEND", b""))
