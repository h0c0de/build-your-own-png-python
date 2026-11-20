"""Irisan 4 — enkoder: round-trip dua arah.

(1) Kita enkode piksel Pillow -> Pillow membaca
balik identik. (2) Kita enkode -> kita dekode
identik. (3) Enkode memakai kompresor build 23:
keluarannya harus terdekode juga oleh zlib stdlib
(lewat Pillow) — sudah dibuktikan (1).
"""
import io

from PIL import Image

import pngku
from uji_bersama import berkas, baca, rgba_pillow

if __name__ == "__main__":
    cek = 0
    for nama in berkas():
        if nama.startswith("x"):
            continue
        harap = rgba_pillow(nama)
        g = pngku.dekode(baca(nama))
        g2 = pngku.Gambar(g.lebar, g.tinggi, 8, 6, 0,
                          harap)
        png_kita = pngku.enkode(g2)
        balik = Image.open(io.BytesIO(png_kita)) \
            .convert("RGBA").tobytes()
        assert balik == harap, (nama, "pillow baca")
        g3 = pngku.dekode(png_kita)
        assert g3.piksel == harap, (nama, "kita baca")
        cek += 2
    print("irisan 4: %d pemeriksaan LULUS" % cek)
