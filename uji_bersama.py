"""Pembanding build 27: Pillow sebagai wasit piksel.

Khusus mode I;16 (grayscale 16-bit): convert('RGBA')
Pillow MENJEPIT nilai ke 255, bukan menggeser —
jadi untuk berkas itu ekspektasi dibangun dari
contoh mentah Pillow sendiri yang digeser >>8.
"""
import os

from PIL import Image

SUITE = os.path.join(os.path.dirname(__file__),
                     "..", "png-ref", "pngsuite",
                     "png")


def berkas(awalan=None):
    hasil = []
    for nama in sorted(os.listdir(SUITE)):
        if nama.endswith(".png") and (
                awalan is None
                or nama.startswith(awalan)):
            hasil.append(nama)
    return hasil


def baca(nama):
    with open(os.path.join(SUITE, nama), "rb") as f:
        return f.read()


def rgba_pillow(nama):
    """RGBA8 ekspektasi menurut Pillow."""
    im = Image.open(os.path.join(SUITE, nama))
    if im.mode == "L" and "transparency" in im.info:
        # Quirk Pillow: piksel abu <8-bit disimpan
        # terskala (x17 utk 4-bit) tetapi nilai
        # transparansinya satuan mentah spek, jadi
        # convert('RGBA') gagal menandainya. Bangun
        # alfa dari contoh Pillow yang diskalakan
        # turun + aturan spek.
        import struct as _s
        with open(os.path.join(SUITE, nama),
                  "rb") as f:
            kepala = f.read(33)
        ked = kepala[24]
        if ked < 8:
            dasar = im.convert("RGB").tobytes()
            mentah = im.tobytes()
            faktor = 255 // ((1 << ked) - 1)
            tval = im.info["transparency"]
            keluar = bytearray()
            for i, v in enumerate(mentah):
                keluar += dasar[i * 3:(i + 1) * 3]
                keluar.append(
                    0 if v // faktor == tval else 255)
            return bytes(keluar)
    if im.mode == "I;16":
        lebar, tinggi = im.size
        mentah = im.tobytes()
        tval = im.info.get("transparency")
        keluar = bytearray()
        for i in range(0, len(mentah), 2):
            penuh = mentah[i] | (mentah[i + 1] << 8)
            v = penuh >> 8
            a = 0 if tval is not None and \
                penuh == tval else 255
            keluar += bytes((v, v, v, a))
        return bytes(keluar)
    return im.convert("RGBA").tobytes()


def beda_piksel(a, b):
    n = 0
    for i in range(0, len(a), 4):
        if a[i:i + 4] != b[i:i + 4]:
            n += 1
    return n
