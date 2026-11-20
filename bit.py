"""I/O bit untuk DEFLATE (RFC 1951 §3.1.1).

Elemen data dikemas mulai dari bit paling tidak
signifikan (LSB) byte-nya; kode Huffman dikemas
mulai dari bit paling signifikan (MSB) kode-nya.
Dua aturan berlawanan ini adalah sumber bug nomor
satu di setiap implementasi DEFLATE.
"""


class GalatDeflate(Exception):
    """Aliran DEFLATE tidak sah."""


class PembacaBit:
    """Membaca bit LSB-first dari bytes."""

    def __init__(self, data):
        self.data = data
        self.pos_byte = 0
        self.pos_bit = 0  # 0..7, bit berikutnya di byte ini

    def baca(self, jumlah):
        """Baca `jumlah` bit sebagai bilangan LSB-first."""
        nilai = 0
        for i in range(jumlah):
            if self.pos_byte >= len(self.data):
                raise GalatDeflate("aliran terpotong")
            bit = (self.data[self.pos_byte] >> self.pos_bit) & 1
            nilai |= bit << i
            self.pos_bit += 1
            if self.pos_bit == 8:
                self.pos_bit = 0
                self.pos_byte += 1
        return nilai

    def sejajarkan(self):
        """Lewati sisa bit sampai batas byte (blok stored)."""
        if self.pos_bit:
            self.pos_bit = 0
            self.pos_byte += 1

    def baca_byte(self, jumlah):
        """Baca byte-byte utuh (harus sedang sejajar)."""
        if self.pos_bit:
            raise GalatDeflate("tidak sejajar byte")
        akhir = self.pos_byte + jumlah
        if akhir > len(self.data):
            raise GalatDeflate("aliran terpotong")
        hasil = self.data[self.pos_byte:akhir]
        self.pos_byte = akhir
        return hasil

    def sisa_byte(self):
        """Byte yang belum terbaca dari posisi sejajar ini."""
        if self.pos_bit:
            raise GalatDeflate("tidak sejajar byte")
        return self.data[self.pos_byte:]


class PenulisBit:
    """Menulis bit LSB-first menjadi bytes."""

    def __init__(self):
        self.keluar = bytearray()
        self.kurung = 0   # akumulator bit berjalan
        self.nbit = 0     # jumlah bit sah di akumulator

    def tulis(self, nilai, jumlah):
        """Tulis `jumlah` bit dari `nilai`, LSB dulu."""
        self.kurung |= (nilai & ((1 << jumlah) - 1)) << self.nbit
        self.nbit += jumlah
        while self.nbit >= 8:
            self.keluar.append(self.kurung & 0xFF)
            self.kurung >>= 8
            self.nbit -= 8

    def tulis_kode(self, kode, panjang):
        """Tulis kode Huffman: bit kode dari MSB ke LSB."""
        for i in range(panjang - 1, -1, -1):
            self.tulis((kode >> i) & 1, 1)

    def sejajarkan(self):
        """Isi sisa byte berjalan dengan nol."""
        if self.nbit:
            self.keluar.append(self.kurung & 0xFF)
            self.kurung = 0
            self.nbit = 0

    def tulis_byte(self, data):
        """Tempel byte utuh (harus sedang sejajar)."""
        if self.nbit:
            raise GalatDeflate("tidak sejajar byte")
        self.keluar.extend(data)

    def hasil(self):
        self.sejajarkan()
        return bytes(self.keluar)
