"""Model data: Kategori, Transaksi (+ turunannya Pemasukan/Pengeluaran), Goals."""
from datetime import datetime
from enum import Enum

from .validasi import wajib_isi

FORMAT_FILE = "%Y-%m-%d %H:%M:%S"    # format waktu di file CSV
FORMAT_TAMPIL = "%d-%m-%Y %H:%M"     # format waktu di tabel UI


class Kategori(Enum):
    """Daftar kategori pengeluaran (padanan enum kategori.java)."""
    MAKANAN = "Makanan"
    TRANSPORTASI = "Transportasi"
    HIBURAN = "Hiburan"
    PENDIDIKAN = "Pendidikan"
    LAINNYA = "Lainnya"


DAFTAR_KATEGORI = [k.value for k in Kategori]


def rupiah(angka):
    """Format angka menjadi 'Rp1.250.000'."""
    return "Rp" + f"{angka:,.0f}".replace(",", ".")


def baca_waktu(teks):
    """Ubah teks waktu di file menjadi objek datetime."""
    return datetime.strptime(teks, FORMAT_FILE)


class Transaksi:
    """Kelas dasar semua transaksi (induk Pemasukan & Pengeluaran)."""
    jenis = "TRANSAKSI"

    def __init__(self, deskripsi, nominal, waktu=None):
        wajib_isi(Deskripsi=deskripsi)
        if nominal <= 0:
            raise ValueError("Nominal transaksi harus lebih dari 0.")
        self.deskripsi = deskripsi.strip()
        self.nominal = float(nominal)
        self.waktu = waktu or datetime.now()

    @property
    def kategori(self):
        """Pemasukan tidak punya kategori."""
        return "-"

    @property
    def waktu_file(self):
        return self.waktu.strftime(FORMAT_FILE)

    @property
    def waktu_teks(self):
        return self.waktu.strftime(FORMAT_TAMPIL)

    def tampilkan(self):
        """Satu baris teks ringkas untuk transaksi."""
        return (f"[{self.waktu_teks}] {self.jenis} | {self.deskripsi} | "
                f"{rupiah(self.nominal)} | Kategori: {self.kategori}")


class Pemasukan(Transaksi):
    """Uang masuk (tabungan / saldo awal)."""
    jenis = "PEMASUKAN"


class Pengeluaran(Transaksi):
    """Uang keluar; punya kategori."""
    jenis = "PENGELUARAN"

    def __init__(self, deskripsi, nominal, kategori, waktu=None):
        super().__init__(deskripsi, nominal, waktu)
        self._kategori = kategori

    @property
    def kategori(self):
        return self._kategori


class Goals:
    """Target tabungan beserta perhitungan progresnya."""

    def __init__(self, nama, target):
        wajib_isi(Nama_goals=nama)
        if target <= 0:
            raise ValueError("Nominal target harus lebih dari 0.")
        self.nama = nama.strip()
        self.target = float(target)

    def hitung_persen(self, saldo):
        """Persentase tercapai, dibatasi 0-100."""
        return max(0.0, min(100.0, saldo / self.target * 100))

    def hitung_sisa(self, saldo):
        """Sisa nominal menuju target (minimal 0)."""
        return max(0.0, self.target - saldo)

    def pesan_motivasi(self, saldo):
        """Kalimat semangat sesuai progres."""
        persen = self.hitung_persen(saldo)
        if persen >= 100:
            return "Selamat! Target tercapai, kamu hebat!"
        if persen >= 75:
            return "Sedikit lagi! Target sudah di depan mata."
        if persen >= 50:
            return "Sudah lebih dari setengah jalan, terus semangat!"
        if persen >= 25:
            return "Awal yang bagus, pertahankan kebiasaan menabungmu!"
        return "Setiap rupiah berarti, ayo mulai menabung!"
