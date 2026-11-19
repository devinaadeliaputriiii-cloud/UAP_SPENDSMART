"""processing: algoritma sorting/searching, filter, dan class Dompet (logika bisnis).

Merge Sort, Linear Search, dan Binary Search ditulis manual agar cara kerjanya
bisa dijelaskan. Dompet mengelola saldo, goals, dan batas anggaran harian.
"""
from datetime import date, datetime

from .fileio import RiwayatFile
from .models import (DAFTAR_KATEGORI, FORMAT_FILE, Goals, Pemasukan, Pengeluaran,
                     baca_waktu, rupiah)
from .validasi import wajib_isi


def merge_sort(data, key=lambda x: x, turun=False):
    """Urutkan `data` dengan Merge Sort - O(n log n) dan stabil.

    key  : fungsi (boleh lambda) pengambil nilai pembanding.
    turun: True untuk urutan besar -> kecil.
    Nilai key dihitung SEKALI per elemen (decorate) agar tidak berulang.
    """
    assert callable(key), "key harus berupa fungsi"
    dekorasi = [(key(x), x) for x in data]
    return [x for _, x in _urut(dekorasi, turun)]


def _urut(pasangan, turun):
    """Bagian rekursif merge sort: pecah dua lalu gabung."""
    if len(pasangan) <= 1:
        return pasangan
    tengah = len(pasangan) // 2
    return _gabung(_urut(pasangan[:tengah], turun), _urut(pasangan[tengah:], turun), turun)


def _gabung(kiri, kanan, turun):
    """Gabungkan dua list terurut; saat nilai sama ambil kiri (menjaga kestabilan)."""
    hasil, i, j = [], 0, 0
    while i < len(kiri) and j < len(kanan):
        ambil_kiri = kiri[i][0] >= kanan[j][0] if turun else kiri[i][0] <= kanan[j][0]
        if ambil_kiri:
            hasil.append(kiri[i])
            i += 1
        else:
            hasil.append(kanan[j])
            j += 1
    return hasil + kiri[i:] + kanan[j:]


def cari_linear(data, kata_kunci, *pengambil_teks):
    """Linear Search kata kunci (tidak peka huruf besar/kecil).

    *pengambil_teks: satu atau lebih fungsi yang mengambil teks dari elemen,
    mis. lambda t: t.deskripsi. Elemen cocok bila salah satu teks memuat kata kunci.
    """
    kata = kata_kunci.strip().lower()
    hasil = []
    for item in data:
        if any(kata in str(ambil(item)).lower() for ambil in pengambil_teks):
            hasil.append(item)
    return hasil


def cari_biner(data_terurut, target, key=lambda x: x):
    """Binary Search - O(log n). `data_terurut` HARUS urut naik menurut `key`.

    Mengembalikan SEMUA elemen yang bernilai sama dengan target.
    """
    kiri, kanan = 0, len(data_terurut) - 1
    ditemukan = -1
    while kiri <= kanan:
        tengah = (kiri + kanan) // 2
        nilai = key(data_terurut[tengah])
        if nilai == target:
            ditemukan = tengah
            kanan = tengah - 1      # terus ke kiri: cari kemunculan pertama
        elif nilai < target:
            kiri = tengah + 1
        else:
            kanan = tengah - 1
    if ditemukan == -1:
        return []
    hasil = []
    while ditemukan < len(data_terurut) and key(data_terurut[ditemukan]) == target:
        hasil.append(data_terurut[ditemukan])
        ditemukan += 1
    return hasil


class SaldoTidakCukupError(ValueError):
    """Dilempar saat pengeluaran melebihi saldo."""


# Kolom tabel -> fungsi (lambda) pengambil nilai untuk pengurutan.
KOLOM_URUT = {
    "waktu": lambda t: t.waktu,
    "jenis": lambda t: t.jenis,
    "kategori": lambda t: t.kategori.lower(),
    "deskripsi": lambda t: t.deskripsi.lower(),
    "nominal": lambda t: t.nominal,
}


def hitung_total(*nominal):
    """Jumlahkan sejumlah angka (memakai *args). Contoh: hitung_total(1, 2, 3) = 6."""
    total = 0.0
    for n in nominal:
        total += n
    return total


def filter_transaksi(daftar, **kriteria):
    """Saring transaksi memakai **kwargs.

    Kriteria yang didukung: jenis, kategori, min_nominal, max_nominal.
    Kriteria bernilai None diabaikan, jadi dari UI bisa dipanggil langsung.
    """
    hasil = list(daftar)
    if kriteria.get("jenis"):
        hasil = [t for t in hasil if t.jenis == kriteria["jenis"]]
    if kriteria.get("kategori"):
        hasil = [t for t in hasil if t.kategori == kriteria["kategori"]]
    if kriteria.get("min_nominal") is not None:
        hasil = [t for t in hasil if t.nominal >= kriteria["min_nominal"]]
    if kriteria.get("max_nominal") is not None:
        hasil = [t for t in hasil if t.nominal <= kriteria["max_nominal"]]
    return hasil


def urutkan_transaksi(daftar, kolom="waktu", turun=False):
    """Urutkan transaksi menurut nama kolom tabel memakai merge sort."""
    if kolom not in KOLOM_URUT:
        raise ValueError(f"Kolom '{kolom}' tidak dikenal.")
    return merge_sort(daftar, key=KOLOM_URUT[kolom], turun=turun)


def cari_transaksi(daftar, kata_kunci):
    """Cari transaksi. Jika kata kunci angka -> Binary Search nominal tepat;
    selain itu -> Linear Search pada deskripsi, kategori, dan jenis."""
    kata = kata_kunci.strip()
    if not kata:
        return list(daftar)
    try:
        angka = float(kata)
    except ValueError:
        return cari_linear(daftar, kata,
                           lambda t: t.deskripsi, lambda t: t.kategori, lambda t: t.jenis)
    terurut = merge_sort(daftar, key=lambda t: t.nominal)
    return cari_biner(terurut, angka, key=lambda t: t.nominal)


class Dompet:
    """Mengelola riwayat, goals, dan batas anggaran harian (padanan Dompet.java)."""

    def __init__(self, file=None):
        self.file = file or RiwayatFile()
        self.goals = []          # daftar Goals (boleh banyak)
        self.riwayat = []
        self.batas = {}          # kategori -> batas harian
        self.baris_rusak = 0

    def muat_dari_file(self):
        """Isi data dari file; baris rusak dilewati. True bila goals sudah ada."""
        for waktu, jenis, kategori, nominal, ket in self.file.baca_semua():
            try:
                nominal = float(nominal)
                if jenis == "GOAL":
                    lama = self.cari_goals(ket)
                    if lama:             # baris GOAL berikutnya dengan nama sama = ubah target
                        lama.target = Goals(ket, nominal).target
                    else:
                        self.goals.append(Goals(ket, nominal))
                elif jenis == "BATAS":
                    self.batas[kategori] = nominal
                elif jenis == "PEMASUKAN":
                    self.riwayat.append(Pemasukan(ket, nominal, baca_waktu(waktu)))
                elif jenis == "PENGELUARAN":
                    self.riwayat.append(Pengeluaran(ket, nominal, kategori, baca_waktu(waktu)))
            except ValueError:
                self.baris_rusak += 1
        return len(self.goals) > 0

    def cari_goals(self, nama):
        """Cari goals menurut nama (tidak peka huruf besar/kecil); None bila tidak ada."""
        for g in self.goals:
            if g.nama.lower() == str(nama).strip().lower():
                return g
        return None

    def tambah_goals(self, goals):
        """Tambah goals baru; raise ValueError bila namanya sudah dipakai."""
        if self.cari_goals(goals.nama) is not None:
            raise ValueError(f"Goals '{goals.nama}' sudah ada.")
        self.goals.append(goals)
        self.file.tulis(_sekarang(), "GOAL", "-", goals.target, goals.nama)

    def goals_tercapai(self):
        """Nama semua goals yang targetnya sudah dicapai oleh saldo sekarang."""
        saldo = self.saldo
        return [g.nama for g in self.goals if saldo >= g.target]

    @property
    def saldo(self):
        masuk = hitung_total(*[t.nominal for t in self.riwayat if isinstance(t, Pemasukan)])
        keluar = hitung_total(*[t.nominal for t in self.riwayat if isinstance(t, Pengeluaran)])
        return masuk - keluar

    def tambah_pemasukan(self, deskripsi, nominal):
        p = Pemasukan(deskripsi, nominal)
        self.riwayat.append(p)
        self.file.tulis(p.waktu_file, p.jenis, "-", p.nominal, p.deskripsi)

    def catat_pengeluaran(self, deskripsi, nominal, kategori):
        """Catat pengeluaran; raise SaldoTidakCukupError bila saldo kurang."""
        wajib_isi(Kategori=kategori)
        if nominal > self.saldo:
            raise SaldoTidakCukupError(f"Saldo kamu hanya {rupiah(self.saldo)}.")
        p = Pengeluaran(deskripsi, nominal, kategori)
        self.riwayat.append(p)
        self.file.tulis(p.waktu_file, p.jenis, kategori, p.nominal, p.deskripsi)

    def atur_batas(self, kategori, batas):
        if batas <= 0:
            raise ValueError("Batas harian harus lebih dari 0.")
        self.batas[kategori] = batas
        self.file.tulis(_sekarang(), "BATAS", kategori, batas, "Batas anggaran")

    def total_pengeluaran(self, kategori, hanya_hari_ini=False):
        """Total pengeluaran sebuah kategori (opsional hanya hari ini)."""
        hasil = filter_transaksi(self.riwayat, jenis="PENGELUARAN", kategori=kategori)
        if hanya_hari_ini:
            hasil = [t for t in hasil if t.waktu.date() == date.today()]
        return hitung_total(*[t.nominal for t in hasil])

    def cek_batas(self, kategori):
        """Pesan peringatan batas harian ('' bila aman / batas belum diatur)."""
        if kategori not in self.batas:
            return ""
        batas = self.batas[kategori]
        total = self.total_pengeluaran(kategori, hanya_hari_ini=True)
        if total > batas:
            return (f"PERINGATAN: pengeluaran {kategori} hari ini ({rupiah(total)}) "
                    f"sudah MELEWATI batas harian {rupiah(batas)}!")
        if total >= batas * 0.8:
            return (f"Hati-hati: pengeluaran {kategori} hari ini sudah {rupiah(total)} "
                    f"dari batas harian {rupiah(batas)}.")
        return ""


    def ringkasan_kategori(self):
        """Return (dict total per kategori, total semua, kategori terbesar / None)."""
        totals = {nama: self.total_pengeluaran(nama) for nama in DAFTAR_KATEGORI}
        total_semua = hitung_total(*totals.values())
        besar = max(totals, key=lambda n: totals[n]) if total_semua > 0 else None
        return totals, total_semua, besar


def _sekarang():
    """Waktu saat ini dalam format file."""
    return datetime.now().strftime(FORMAT_FILE)
