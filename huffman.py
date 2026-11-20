"""Kode Huffman kanonik (RFC 1951 §3.2.2).

Sebuah kode Huffman di DEFLATE sepenuhnya ditentukan
oleh PANJANG kode tiap simbol: kode diberikan secara
kanonik — urut menurut (panjang, simbol) — sehingga
pengirim cukup mengirim daftar panjangnya saja.
"""

from bit import GalatDeflate

PANJANG_MAKS = 15


def bangun_tabel(panjang):
    """Dari daftar panjang kode -> tabel dekode.

    Mengembalikan dict (panjang, kode) -> simbol.
    Panjang 0 berarti simbol tidak dipakai. Kode yang
    over-subscribed ditolak; kode tak lengkap ditolak
    kecuali kasus khusus satu simbol berjarak (yang
    memang dihasilkan zlib untuk alfabet jarak).
    """
    maks = max(panjang) if panjang else 0
    # hitung kode berikutnya per panjang (algoritma RFC)
    bl_count = [0] * (maks + 1)
    for p in panjang:
        if p:
            bl_count[p] += 1
    next_code = [0] * (maks + 2)
    kode = 0
    for bit in range(1, maks + 1):
        kode = (kode + bl_count[bit - 1]) << 1
        next_code[bit] = kode
    tabel = {}
    for simbol, p in enumerate(panjang):
        if p:
            tabel[(p, next_code[p])] = simbol
            next_code[p] += 1
    # validasi: periksa Kraft — over-subscribed = galat;
    # tak lengkap hanya boleh untuk tepat satu kode
    # (kasus alfabet jarak satu simbol) atau kosong.
    if maks:
        sisa = 1
        for bit in range(1, maks + 1):
            sisa <<= 1
            sisa -= bl_count[bit]
            if sisa < 0:
                raise GalatDeflate("kode Huffman over-subscribed")
        dipakai = sum(1 for p in panjang if p)
        if sisa > 0 and dipakai > 1:
            raise GalatDeflate("kode Huffman tidak lengkap")
    return tabel


def dekode(pembaca, tabel):
    """Baca satu simbol dari aliran bit."""
    kode = 0
    panjang = 0
    while panjang <= PANJANG_MAKS:
        kode = (kode << 1) | pembaca.baca(1)
        panjang += 1
        simbol = tabel.get((panjang, kode))
        if simbol is not None:
            return simbol
    raise GalatDeflate("kode Huffman tidak dikenal")


def kode_kanonik(panjang):
    """Dari daftar panjang -> daftar (kode, panjang).

    Sisi pengirim: pasangan yang harus ditulis untuk
    tiap simbol (simbol berpanjang 0 -> (0, 0)).
    """
    maks = max(panjang) if panjang else 0
    bl_count = [0] * (maks + 1)
    for p in panjang:
        if p:
            bl_count[p] += 1
    next_code = [0] * (maks + 2)
    kode = 0
    for bit in range(1, maks + 1):
        kode = (kode + bl_count[bit - 1]) << 1
        next_code[bit] = kode
    hasil = []
    for p in panjang:
        if p:
            hasil.append((next_code[p], p))
            next_code[p] += 1
        else:
            hasil.append((0, 0))
    return hasil


def panjang_dari_frekuensi(freq, batas=PANJANG_MAKS):
    """Panjang kode Huffman optimal terbatas `batas`.

    Memakai algoritma package-merge: panjang yang
    dihasilkan optimal di antara semua kode dengan
    panjang maksimum `batas`, untuk alfabet sampai
    ribuan simbol dan batas 15 ini jauh lebih sederhana
    dibuktikan benar daripada penyesuaian luapan ala
    pohon.
    """
    simbol_aktif = [s for s, f in enumerate(freq) if f > 0]
    if not simbol_aktif:
        return [0] * len(freq)
    if len(simbol_aktif) == 1:
        hasil = [0] * len(freq)
        hasil[simbol_aktif[0]] = 1
        return hasil
    # package-merge: daftar berisi (bobot, {simbol: cacah})
    # digabung berpasangan dari yang teringan, `batas` kali.
    awal = sorted((freq[s], (s,)) for s in simbol_aktif)
    daftar = list(awal)
    for _ in range(batas - 1):
        paket = []
        for i in range(0, len(daftar) - 1, 2):
            bobot = daftar[i][0] + daftar[i + 1][0]
            isi = daftar[i][1] + daftar[i + 1][1]
            paket.append((bobot, isi))
        # gabung paket dengan daftar awal, urut bobot
        daftar = sorted(awal + paket)
    # 2n-2 entri pertama menentukan kedalaman tiap simbol
    kedalaman = [0] * len(freq)
    for _, isi in daftar[:2 * len(simbol_aktif) - 2]:
        for s in isi:
            kedalaman[s] += 1
    return kedalaman
