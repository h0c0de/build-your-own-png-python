"""DEFLATE (RFC 1951): inflate + deflate.

Formatnya adalah rangkaian blok; tiap blok diawali
BFINAL (1 bit) dan BTYPE (2 bit): 00 stored,
01 Huffman tetap, 10 Huffman dinamis, 11 terlarang.
Blok terkompresi adalah aliran simbol literal/length
yang diakhiri simbol 256, dengan pasangan
length-distance merujuk salinan dari keluaran yang
sudah dihasilkan (jendela geser 32 KiB, LZ77).
"""

from bit import PembacaBit, PenulisBit, GalatDeflate
import huffman

# §3.2.5: basis panjang & bit ekstra untuk kode
# length 257..285, dan basis jarak & bit ekstra
# untuk kode jarak 0..29.
BASIS_PANJANG = [
    3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23,
    27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131,
    163, 195, 227, 258]
EKSTRA_PANJANG = [
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
    3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0]
BASIS_JARAK = [
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97,
    129, 193, 257, 385, 513, 769, 1025, 1537, 2049,
    3073, 4097, 6145, 8193, 12289, 16385, 24577]
EKSTRA_JARAK = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
    7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]

# §3.2.7: urutan transmisi panjang kode untuk alfabet
# panjang-kode pada header dinamis.
URUTAN_PK = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4,
             12, 3, 13, 2, 14, 1, 15]

JENDELA = 32768
PANJANG_MIN = 3
PANJANG_MAKS_MATCH = 258


def _panjang_tetap():
    # §3.2.6: literal/length 0-143:8, 144-255:9,
    # 256-279:7, 280-287:8; jarak 0-31 semua 5 bit
    # (30-31 tidak pernah muncul, tapi panjangnya
    # terdefinisi — tanpanya kode terhitung tak lengkap)
    lit = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
    jar = [5] * 32
    return lit, jar


_TABEL_TETAP = None


def _tabel_tetap():
    global _TABEL_TETAP
    if _TABEL_TETAP is None:
        lit, jar = _panjang_tetap()
        _TABEL_TETAP = (huffman.bangun_tabel(lit),
                        huffman.bangun_tabel(jar))
    return _TABEL_TETAP


def _tiup_blok_terkompresi(pembaca, tabel_lit, tabel_jar,
                           keluar):
    while True:
        simbol = huffman.dekode(pembaca, tabel_lit)
        if simbol < 256:
            keluar.append(simbol)
        elif simbol == 256:
            return
        else:
            idx = simbol - 257
            if idx >= len(BASIS_PANJANG):
                raise GalatDeflate("kode length tidak sah")
            panjang = BASIS_PANJANG[idx] + \
                pembaca.baca(EKSTRA_PANJANG[idx])
            dj = huffman.dekode(pembaca, tabel_jar)
            if dj >= len(BASIS_JARAK):
                raise GalatDeflate("kode jarak tidak sah")
            jarak = BASIS_JARAK[dj] + \
                pembaca.baca(EKSTRA_JARAK[dj])
            if jarak > len(keluar):
                raise GalatDeflate("jarak terlalu jauh ke belakang")
            # salinan boleh tumpang tindih sumbernya
            # (begitulah run dienkode)
            awal = len(keluar) - jarak
            for i in range(panjang):
                keluar.append(keluar[awal + i])


def _baca_tabel_dinamis(pembaca):
    hlit = pembaca.baca(5) + 257
    hdist = pembaca.baca(5) + 1
    hclen = pembaca.baca(4) + 4
    pk = [0] * 19
    for i in range(hclen):
        pk[URUTAN_PK[i]] = pembaca.baca(3)
    tabel_pk = huffman.bangun_tabel(pk)
    total = hlit + hdist
    panjang = []
    while len(panjang) < total:
        simbol = huffman.dekode(pembaca, tabel_pk)
        if simbol < 16:
            panjang.append(simbol)
        elif simbol == 16:
            if not panjang:
                raise GalatDeflate("simbol 16 tanpa pendahulu")
            ulang = 3 + pembaca.baca(2)
            panjang.extend([panjang[-1]] * ulang)
        elif simbol == 17:
            ulang = 3 + pembaca.baca(3)
            panjang.extend([0] * ulang)
        else:  # 18
            ulang = 11 + pembaca.baca(7)
            panjang.extend([0] * ulang)
    if len(panjang) > total:
        raise GalatDeflate("panjang kode dinamis berlebih")
    lit = panjang[:hlit]
    jar = panjang[hlit:]
    if lit[256] == 0:
        raise GalatDeflate("kode akhir-blok (256) hilang")
    return huffman.bangun_tabel(lit), huffman.bangun_tabel(jar)


def tiup(data):
    """Dekompresi aliran DEFLATE mentah -> bytes."""
    pembaca = PembacaBit(data)
    keluar = bytearray()
    while True:
        bfinal = pembaca.baca(1)
        btype = pembaca.baca(2)
        if btype == 0:
            pembaca.sejajarkan()
            kepala = pembaca.baca_byte(4)
            ln = kepala[0] | (kepala[1] << 8)
            nln = kepala[2] | (kepala[3] << 8)
            if ln != (nln ^ 0xFFFF):
                raise GalatDeflate("LEN/NLEN blok stored tak cocok")
            keluar.extend(pembaca.baca_byte(ln))
        elif btype == 1:
            tl, tj = _tabel_tetap()
            _tiup_blok_terkompresi(pembaca, tl, tj, keluar)
        elif btype == 2:
            tl, tj = _baca_tabel_dinamis(pembaca)
            _tiup_blok_terkompresi(pembaca, tl, tj, keluar)
        else:
            raise GalatDeflate("BTYPE=11 terlarang")
        if bfinal:
            return bytes(keluar)


# ---------- Kompresor (Irisan 4-5) ----------

def _hash3(data, i):
    return ((data[i] << 10) ^ (data[i + 1] << 5)
            ^ data[i + 2]) & 0x7FFF


def _panjang_cocok(data, a, b, maks):
    """Panjang kecocokan data[a:] vs data[b:] (b < a)."""
    l = 0
    while l < maks:
        potong = min(32, maks - l)
        if data[a + l:a + l + potong] == \
                data[b + l:b + l + potong]:
            l += potong
        else:
            while l < maks and data[a + l] == data[b + l]:
                l += 1
            break
    return l


def _tokenisasi(data):
    """LZ77: rantai hash + pencocokan lazy satu langkah.

    Token: (byte,) untuk literal, (panjang, jarak)
    untuk rujukan. Jendela 32 KiB, panjang 3..258.
    """
    n = len(data)
    token = []
    kepala = {}
    sebelum = {}

    def masukkan(i):
        if i + 2 < n:
            h = _hash3(data, i)
            sebelum[i] = kepala.get(h, -1)
            kepala[h] = i

    def cari(pos):
        if pos + 2 >= n:
            return 0, 0
        maks = min(PANJANG_MAKS_MATCH, n - pos)
        cand = kepala.get(_hash3(data, pos), -1)
        terbaik, jarak_t = 0, 0
        probe = 0
        while cand != -1 and pos - cand <= JENDELA \
                and probe < 128:
            l = _panjang_cocok(data, pos, cand, maks)
            if l >= PANJANG_MIN and l > terbaik:
                terbaik, jarak_t = l, pos - cand
                if l >= maks:
                    break
            cand = sebelum.get(cand, -1)
            probe += 1
        return terbaik, jarak_t

    pos = 0
    while pos < n:
        panjang, jarak = cari(pos)
        if panjang >= PANJANG_MIN and pos + 1 < n:
            p2, _ = cari(pos + 1)
            if p2 > panjang:
                token.append((data[pos],))
                masukkan(pos)
                pos += 1
                continue
        if panjang >= PANJANG_MIN:
            token.append((panjang, jarak))
            for k in range(pos, pos + panjang):
                masukkan(k)
            pos += panjang
        else:
            token.append((data[pos],))
            masukkan(pos)
            pos += 1
    return token


def _kode_panjang(panjang):
    """Panjang match -> (simbol, nilai ekstra, bit ekstra)."""
    if panjang == 258:
        return 285, 0, 0
    for i in range(28):
        if BASIS_PANJANG[i] <= panjang <= \
                BASIS_PANJANG[i] + (1 << EKSTRA_PANJANG[i]) - 1:
            return 257 + i, panjang - BASIS_PANJANG[i], \
                EKSTRA_PANJANG[i]
    raise GalatDeflate("panjang match di luar tabel")


def _kode_jarak(jarak):
    for i in range(30):
        if BASIS_JARAK[i] <= jarak <= \
                BASIS_JARAK[i] + (1 << EKSTRA_JARAK[i]) - 1:
            return i, jarak - BASIS_JARAK[i], EKSTRA_JARAK[i]
    raise GalatDeflate("jarak di luar tabel")


def _tulis_token(penulis, token, kode_lit, kode_jar):
    for t in token:
        if len(t) == 1:
            k, p = kode_lit[t[0]]
            penulis.tulis_kode(k, p)
        else:
            panjang, jarak = t
            simbol, ekstra, nbit = _kode_panjang(panjang)
            k, p = kode_lit[simbol]
            penulis.tulis_kode(k, p)
            if nbit:
                penulis.tulis(ekstra, nbit)
            simbol_j, ekstra_j, nbit_j = _kode_jarak(jarak)
            k, p = kode_jar[simbol_j]
            penulis.tulis_kode(k, p)
            if nbit_j:
                penulis.tulis(ekstra_j, nbit_j)
    k, p = kode_lit[256]
    penulis.tulis_kode(k, p)


def _blok_stored(data, final):
    # LEN 16 bit: pecah per 65535 byte; hanya potongan
    # terakhir yang membawa BFINAL
    keluar = bytearray()
    potongan = [data[i:i + 65535]
                for i in range(0, len(data), 65535)] or [b""]
    for j, pot in enumerate(potongan):
        p = PenulisBit()
        p.tulis(1 if (final and j == len(potongan) - 1)
                else 0, 1)
        p.tulis(0, 2)
        p.sejajarkan()
        ln = len(pot)
        p.tulis_byte(ln.to_bytes(2, "little"))
        p.tulis_byte((ln ^ 0xFFFF).to_bytes(2, "little"))
        p.tulis_byte(pot)
        keluar.extend(p.hasil())
    return bytes(keluar)


def _blok_tetap(token, final):
    lit_p, jar_p = _panjang_tetap()
    penulis = PenulisBit()
    penulis.tulis(1 if final else 0, 1)
    penulis.tulis(1, 2)
    _tulis_token(penulis, token,
                 huffman.kode_kanonik(lit_p),
                 huffman.kode_kanonik(jar_p))
    return penulis.hasil()


def _rle_panjang(gabungan):
    """Encode daftar panjang kode -> token alfabet
    panjang-kode (simbol, ekstra, bit ekstra)."""
    token = []
    i, n = 0, len(gabungan)
    while i < n:
        v = gabungan[i]
        run = 1
        while i + run < n and gabungan[i + run] == v:
            run += 1
        if v == 0:
            sisa = run
            while sisa >= 11:
                ambil = min(sisa, 138)
                token.append((18, ambil - 11, 7))
                sisa -= ambil
            if sisa >= 3:
                token.append((17, sisa - 3, 3))
                sisa = 0
            token.extend([(0, 0, 0)] * sisa)
        else:
            token.append((v, 0, 0))
            sisa = run - 1
            while sisa >= 3:
                ambil = min(sisa, 6)
                token.append((16, ambil - 3, 2))
                sisa -= ambil
            token.extend([(v, 0, 0)] * sisa)
        i += run
    return token


def _blok_dinamis(token, freq_lit, freq_jar, final):
    lit_p = huffman.panjang_dari_frekuensi(freq_lit)
    jar_p = huffman.panjang_dari_frekuensi(freq_jar)
    # potong nol di ekor (HLIT minimal 257, HDIST min 1)
    hlit = 288
    while hlit > 257 and lit_p[hlit - 1] == 0:
        hlit -= 1
    hdist = 30
    while hdist > 1 and jar_p[hdist - 1] == 0:
        hdist -= 1
    gabungan = lit_p[:hlit] + jar_p[:hdist]
    rle = _rle_panjang(gabungan)
    freq_pk = [0] * 19
    for simbol, _, _ in rle:
        freq_pk[simbol] += 1
    pk_p = huffman.panjang_dari_frekuensi(freq_pk, batas=7)
    hclen = 19
    while hclen > 4 and pk_p[URUTAN_PK[hclen - 1]] == 0:
        hclen -= 1
    penulis = PenulisBit()
    penulis.tulis(1 if final else 0, 1)
    penulis.tulis(2, 2)
    penulis.tulis(hlit - 257, 5)
    penulis.tulis(hdist - 1, 5)
    penulis.tulis(hclen - 4, 4)
    for i in range(hclen):
        penulis.tulis(pk_p[URUTAN_PK[i]], 3)
    kode_pk = huffman.kode_kanonik(pk_p)
    for simbol, ekstra, nbit in rle:
        k, p = kode_pk[simbol]
        penulis.tulis_kode(k, p)
        if nbit:
            penulis.tulis(ekstra, nbit)
    _tulis_token(penulis, token,
                 huffman.kode_kanonik(lit_p),
                 huffman.kode_kanonik(jar_p))
    return penulis.hasil()


def padat(data):
    """Kompresi bytes -> aliran DEFLATE mentah.

    Satu blok terkompresi untuk seluruh data (atau
    blok stored bila itu yang terkecil); pilihan
    stored/tetap/dinamis berdasarkan ukuran nyata.
    """
    if not data:
        penulis = PenulisBit()
        penulis.tulis(1, 1)
        penulis.tulis(1, 2)
        k, p = huffman.kode_kanonik(_panjang_tetap()[0])[256]
        penulis.tulis_kode(k, p)
        return penulis.hasil()
    token = _tokenisasi(data)
    freq_lit = [0] * 288
    freq_jar = [0] * 30
    for t in token:
        if len(t) == 1:
            freq_lit[t[0]] += 1
        else:
            freq_lit[_kode_panjang(t[0])[0]] += 1
            freq_jar[_kode_jarak(t[1])[0]] += 1
    freq_lit[256] += 1
    if not any(freq_jar):
        freq_jar[0] = 1  # kode jarak boneka satu simbol
    kandidat = [_blok_stored(data, True),
                _blok_tetap(token, True),
                _blok_dinamis(token, freq_lit, freq_jar, True)]
    return min(kandidat, key=len)
