"""Irisan 3 — Adam7 + sapuan penuh + kunci IDAT.

(1) basi*/oi* identik Pillow. (2) Semua berkas
suite non-x yang belum tercakup ikut disapu.
(3) Setiap aliran IDAT di suite: inflate build 23
== zlib stdlib byte demi byte.
"""
import zlib

import pngku
from pampat import dekompres
from uji_bersama import berkas, baca, rgba_pillow, \
    beda_piksel


def idat_dari(data):
    pos = 8
    gabung = bytearray()
    while pos < len(data):
        tipe, isi, pos = pngku._baca_chunk(data, pos)
        if tipe == b"IDAT":
            gabung += isi
        if tipe == b"IEND":
            break
    return bytes(gabung)


if __name__ == "__main__":
    cek = 0
    for nama in berkas():
        if nama.startswith("x"):
            continue
        data = baca(nama)
        g = pngku.dekode(data)
        harap = rgba_pillow(nama)
        assert len(harap) == len(g.piksel), nama
        b = beda_piksel(g.piksel, harap)
        assert b == 0, (nama, b)
        cek += 1
        aliran = idat_dari(data)
        if aliran:
            assert dekompres(aliran) == \
                zlib.decompress(aliran), nama
            cek += 1
    print("irisan 3: %d pemeriksaan LULUS" % cek)
