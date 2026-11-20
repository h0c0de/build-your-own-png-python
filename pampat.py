"""Titik masuk build 23: DEFLATE + zlib + gzip.

    from pampat import kompres, dekompres
    bulat = dekompres(kompres(b"halo halo halo"))

`kompres`/`dekompres` memakai format zlib (RFC 1950);
varian `*_mentah` bekerja pada aliran DEFLATE mentah
(RFC 1951) dan `*_gzip` pada format gzip (RFC 1952).
"""

import bungkus
import deflate as _deflate


def dekompres(aliran_zlib):
    return bungkus.buka_zlib(aliran_zlib)


def dekompres_mentah(aliran_deflate):
    return _deflate.tiup(aliran_deflate)


def dekompres_gzip(aliran_gzip):
    return bungkus.buka_gzip(aliran_gzip)


def kompres(data, level=6):
    """Kompresi bytes -> format zlib (RFC 1950)."""
    return bungkus.bungkus_zlib(_deflate.padat(data), data,
                                level=level)


def kompres_mentah(data):
    """Kompresi bytes -> aliran DEFLATE mentah."""
    return _deflate.padat(data)


def kompres_gzip(data):
    """Kompresi bytes -> format gzip (RFC 1952)."""
    return bungkus.bungkus_gzip(_deflate.padat(data), data)
