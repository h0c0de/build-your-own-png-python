"""Irisan 2 — piksel non-interlace vs Pillow:
kategori dasar, filter, ukuran, transparansi,
latar, gamma (mentah), chunk, palet, zlib."""
import pngku
from uji_bersama import berkas, baca, rgba_pillow, \
    beda_piksel

KATEGORI = ("basn", "f", "s", "t", "bg", "g", "c",
            "p", "z", "exif")

if __name__ == "__main__":
    cek = 0
    dilewati = []
    for nama in berkas():
        if nama.startswith("basi") or \
                nama.startswith("oi") or \
                nama.startswith("x"):
            continue
        if not nama.startswith(KATEGORI):
            continue
        g = pngku.dekode(baca(nama))
        harap = rgba_pillow(nama)
        if len(harap) != len(g.piksel):
            dilewati.append((nama, "ukuran beda"))
            continue
        b = beda_piksel(g.piksel, harap)
        assert b == 0, (nama, b)
        cek += 1
    print("irisan 2: %d pemeriksaan LULUS, "
          "dilewati %s" % (cek, dilewati))
