"""Bungkus zlib (RFC 1950) & gzip (RFC 1952).

DEFLATE mentah tidak membawa pemeriksaan integritas;
zlib menambahkan header 2 byte (CMF/FLG dengan
FCHECK) dan ekor Adler-32 dari data aslinya. gzip
menambahkan header 10 byte, CRC-32, dan ukuran asli.
Checksum di sini ditulis dari definisinya, bukan
diambil dari zlib — wasitnya tetap zlib asli.
"""

import deflate as _deflate
from bit import GalatDeflate


def adler32(data):
    """Adler-32 (RFC 1950 §9): dua jumlah modulo 65521."""
    MOD = 65521
    a, b = 1, 0
    for potong in range(0, len(data), 5552):
        for byte in data[potong:potong + 5552]:
            a += byte
            b += a
        a %= MOD
        b %= MOD
    return ((b << 16) | a) & 0xFFFFFFFF


def _buat_tabel_crc():
    tabel = []
    for n in range(256):
        c = n
        for _ in range(8):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        tabel.append(c)
    return tabel


_TABEL_CRC = _buat_tabel_crc()


def crc32(data):
    """CRC-32 (polinom 0xEDB88320, tercermin)."""
    c = 0xFFFFFFFF
    for byte in data:
        c = _TABEL_CRC[(c ^ byte) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF


def bungkus_zlib(data_mentah_deflate, data_asli, level=6):
    cmf = 0x78  # jendela 32K, metode deflate
    flevel = 0 if level < 2 else (1 if level < 6
                                  else (2 if level == 6 else 3))
    flg = flevel << 6
    flg |= (31 - ((cmf * 256 + flg) % 31)) % 31
    ekor = adler32(data_asli).to_bytes(4, "big")
    return bytes([cmf, flg]) + data_mentah_deflate + ekor


def buka_zlib(aliran):
    """Dekompresi format zlib, memverifikasi header
    dan Adler-32."""
    if len(aliran) < 6:
        raise GalatDeflate("aliran zlib terlalu pendek")
    cmf, flg = aliran[0], aliran[1]
    if (cmf * 256 + flg) % 31 != 0:
        raise GalatDeflate("FCHECK header zlib gagal")
    if cmf & 0x0F != 8:
        raise GalatDeflate("metode bukan deflate")
    if cmf >> 4 > 7:
        raise GalatDeflate("jendela zlib terlalu besar")
    if flg & 0x20:
        raise GalatDeflate("kamus preset tidak didukung")
    hasil = _deflate.tiup(aliran[2:-4])
    harap = int.from_bytes(aliran[-4:], "big")
    if adler32(hasil) != harap:
        raise GalatDeflate("Adler-32 tidak cocok")
    return hasil


def bungkus_gzip(data_mentah_deflate, data_asli):
    kepala = bytes([0x1F, 0x8B, 8, 0]) + \
        (0).to_bytes(4, "little") + bytes([0, 3])
    ekor = crc32(data_asli).to_bytes(4, "little") + \
        (len(data_asli) & 0xFFFFFFFF).to_bytes(4, "little")
    return kepala + data_mentah_deflate + ekor


def buka_gzip(aliran):
    """Dekompresi satu anggota gzip (tanpa FEXTRA/
    FNAME/FCOMMENT/FHCRC — ditolak bila ada)."""
    if len(aliran) < 18 or aliran[0] != 0x1F \
            or aliran[1] != 0x8B:
        raise GalatDeflate("sihir gzip tidak dikenal")
    if aliran[2] != 8:
        raise GalatDeflate("metode gzip bukan deflate")
    if aliran[3] != 0:
        raise GalatDeflate("flag gzip tidak didukung")
    hasil = _deflate.tiup(aliran[10:-8])
    crc = int.from_bytes(aliran[-8:-4], "little")
    isize = int.from_bytes(aliran[-4:], "little")
    if crc32(hasil) != crc:
        raise GalatDeflate("CRC-32 gzip tidak cocok")
    if len(hasil) & 0xFFFFFFFF != isize:
        raise GalatDeflate("ISIZE gzip tidak cocok")
    return hasil
