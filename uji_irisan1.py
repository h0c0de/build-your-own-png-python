"""Irisan 1 — kerangka chunk, CRC, IHDR.

Kode nama berkas PngSuite adalah spek mini:
huruf tipe (0g/2c/3p/4a/6a) + kedalaman 2 digit
+ i/n interlace. Header setiap berkas sah harus
cocok dengan namanya; berkas korup x* harus
ditolak; CRC yang dirusak harus tertangkap.
"""
import struct

import pngku
from uji_bersama import berkas, baca

TIPE_DARI_KODE = {"0g": 0, "2c": 2, "3p": 3,
                  "4a": 4, "6a": 6}

if __name__ == "__main__":
    cek = 0
    cocok_nama = 0
    for nama in berkas():
        if nama.startswith("x"):
            continue
        data = baca(nama)
        tipe, isi, _ = pngku._baca_chunk(data, 8)
        assert tipe == b"IHDR", nama
        lebar, tinggi, ked, tw, _, _, antar = \
            struct.unpack(">IIBBBBB", isi)
        kode = nama[4:6]
        if nama.startswith("bas") and \
                kode in TIPE_DARI_KODE:
            assert tw == TIPE_DARI_KODE[kode], \
                (nama, tw)
            assert ked == int(nama[6:8]), nama
            # interlace ada di awalan: basn/basi
            assert antar == (1 if nama[3] == "i"
                             else 0), nama
            cocok_nama += 1
        cek += 1
    assert cocok_nama >= 30, cocok_nama
    # semua berkas korup resmi ditolak
    korup = berkas("x")
    assert len(korup) == 14
    for nama in korup:
        try:
            pngku.dekode(baca(nama))
        except pngku.GalatPNG:
            cek += 1
            continue
        raise AssertionError("korup diterima: " + nama)
    # CRC dirusak tangan -> tertangkap
    data = bytearray(baca("basn2c08.png"))
    data[40] ^= 0xFF
    try:
        pngku.dekode(bytes(data))
        raise AssertionError("CRC rusak diterima")
    except pngku.GalatPNG:
        cek += 1
    # tanda tangan salah -> tertangkap
    try:
        pngku.dekode(b"bukan png sama sekali")
        raise AssertionError("tanda tangan diterima")
    except pngku.GalatPNG:
        cek += 1
    print("irisan 1: %d pemeriksaan LULUS" % cek)
