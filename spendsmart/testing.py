"""testing: unit test SpendSmart (unittest) - menguji logika TANPA UI.

Jalankan dari folder proyek:  python -m unittest spendsmart.testing -v
"""
import os
import tempfile
import unittest

from .fileio import RiwayatFile
from .models import Goals, Pemasukan, Pengeluaran
from .processing import (Dompet, SaldoTidakCukupError, cari_biner, cari_linear, cari_transaksi,
                         filter_transaksi, hitung_total, merge_sort, urutkan_transaksi)
from .validasi import FormatAngkaError, baca_angka, baca_nominal, wajib_isi


class TestSpendSmart(unittest.TestCase):
    """Kumpulan uji untuk pengolahan data, pencarian, dan pengurutan."""

    def setUp(self):
        """Siapkan Dompet dengan file sementara agar tidak menyentuh data asli."""
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "uji.csv")
        self.dompet = Dompet(RiwayatFile(self.path))
        self.dompet.tambah_pemasukan("Saldo awal", 100000)
        self.dompet.catat_pengeluaran("Makan siang", 25000, "Makanan")
        self.dompet.catat_pengeluaran("Ojek online", 15000, "Transportasi")
        self.dompet.catat_pengeluaran("Makan malam", 25000, "Makanan")

    def tearDown(self):
        self.folder.cleanup()

    def test_saldo_dihitung_benar(self):
        self.assertEqual(self.dompet.saldo, 35000)

    def test_pengeluaran_melebihi_saldo_ditolak(self):
        with self.assertRaises(SaldoTidakCukupError):
            self.dompet.catat_pengeluaran("Laptop", 999999, "Lainnya")

    def test_validasi_input(self):
        self.assertEqual(baca_nominal("25000"), 25000.0)
        for buruk in ("abc", "-5", "0", "nan"):
            with self.assertRaises(ValueError):
                baca_nominal(buruk)
        with self.assertRaises(ValueError):
            wajib_isi(Deskripsi="  ", Nominal="10")

    def test_merge_sort_naik_dan_turun(self):
        self.assertEqual(merge_sort([5, 2, 9, 1, 2]), [1, 2, 2, 5, 9])
        self.assertEqual(merge_sort([5, 2, 9, 1], turun=True), [9, 5, 2, 1])

    def test_urutkan_transaksi_berdasarkan_nominal(self):
        hasil = urutkan_transaksi(self.dompet.riwayat, "nominal", turun=True)
        nominal = [t.nominal for t in hasil]
        self.assertEqual(nominal, sorted(nominal, reverse=True))
        with self.assertRaises(ValueError):
            urutkan_transaksi(self.dompet.riwayat, "kolom_palsu")

    def test_cari_kata_kunci_linear(self):
        hasil = cari_transaksi(self.dompet.riwayat, "makan")
        self.assertEqual(len(hasil), 2)
        self.assertTrue(all("Makan" in t.deskripsi for t in hasil))
        self.assertEqual(cari_transaksi(self.dompet.riwayat, "tidakada"), [])

    def test_cari_nominal_biner(self):
        hasil = cari_transaksi(self.dompet.riwayat, "25000")
        self.assertEqual(len(hasil), 2)
        self.assertEqual(cari_biner([1, 3, 3, 3, 7], 3), [3, 3, 3])
        self.assertEqual(cari_biner([1, 3, 7], 4), [])

    def test_filter_kwargs_dan_total_args(self):
        makan = filter_transaksi(self.dompet.riwayat, kategori="Makanan")
        self.assertEqual(len(makan), 2)
        besar = filter_transaksi(self.dompet.riwayat, min_nominal=20000, jenis="PENGELUARAN")
        self.assertEqual(len(besar), 2)
        self.assertEqual(hitung_total(1, 2, 3.5), 6.5)

    def test_simpan_lalu_muat_ulang(self):
        self.dompet.tambah_goals(Goals("Laptop", 5000000))
        self.dompet.atur_batas("Makanan", 50000)
        baru = Dompet(RiwayatFile(self.path))
        self.assertTrue(baru.muat_dari_file())
        self.assertEqual(baru.saldo, 35000)
        self.assertEqual(baru.goals[0].nama, "Laptop")
        self.assertEqual(baru.batas["Makanan"], 50000)

    def test_file_hilang_dan_rusak_tidak_crash(self):
        kosong = Dompet(RiwayatFile(os.path.join(self.folder.name, "tidak_ada.csv")))
        self.assertFalse(kosong.muat_dari_file())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("rusak,PEMASUKAN,-,bukan_angka,x\n")
        baru = Dompet(RiwayatFile(self.path))
        baru.muat_dari_file()
        self.assertEqual(baru.baris_rusak, 1)

    def test_goals_persen_dibatasi(self):
        g = Goals("Liburan", 1000)
        self.assertEqual(g.hitung_persen(500), 50)
        self.assertEqual(g.hitung_persen(5000), 100)
        self.assertEqual(g.hitung_persen(-10), 0)
        with self.assertRaises(ValueError):
            Goals("X", 0)

    def test_transaksi_nominal_negatif_ditolak(self):
        with self.assertRaises(ValueError):
            Pemasukan("Salah", -5)
        with self.assertRaises(ValueError):
            Pengeluaran("Salah", 0, "Makanan")

    def test_kategori_pemasukan_adalah_strip(self):
        self.assertEqual(Pemasukan("Gaji", 10).kategori, "-")
        self.assertEqual(Pengeluaran("Bakso", 10, "Makanan").kategori, "Makanan")

    def test_pesan_motivasi_sesuai_progres(self):
        g = Goals("Liburan", 1000)
        self.assertIn("Selamat", g.pesan_motivasi(1000))
        self.assertIn("mulai", g.pesan_motivasi(0))
        self.assertEqual(g.hitung_sisa(400), 600)

    def test_cek_batas_peringatan_dan_aman(self):
        self.assertEqual(self.dompet.cek_batas("Makanan"), "")   # batas belum diatur
        self.dompet.atur_batas("Makanan", 30000)                 # hari ini sudah 50000
        self.assertIn("PERINGATAN", self.dompet.cek_batas("Makanan"))
        self.dompet.atur_batas("Transportasi", 100000)
        self.assertEqual(self.dompet.cek_batas("Transportasi"), "")

    def test_ekspor_csv_menulis_header_dan_baris(self):
        tujuan = os.path.join(self.folder.name, "ekspor.csv")
        self.dompet.file.ekspor(tujuan, self.dompet.riwayat)
        with open(tujuan, "r", encoding="utf-8") as f:
            baris = f.read().strip().splitlines()
        self.assertEqual(baris[0], "waktu,jenis,kategori,nominal,keterangan")
        self.assertEqual(len(baris), 1 + len(self.dompet.riwayat))

    def test_ringkasan_kategori(self):
        totals, total, besar = self.dompet.ringkasan_kategori()
        self.assertEqual(totals["Makanan"], 50000)
        self.assertEqual(total, 65000)
        self.assertEqual(besar, "Makanan")

    def test_cari_kosong_mengembalikan_semua(self):
        self.assertEqual(len(cari_transaksi(self.dompet.riwayat, "  ")), len(self.dompet.riwayat))

    def test_merge_sort_stabil(self):
        data = [(1, "a"), (0, "b"), (1, "c")]
        self.assertEqual(merge_sort(data, key=lambda x: x[0]), [(0, "b"), (1, "a"), (1, "c")])

    def test_cari_linear_banyak_kolom(self):
        hasil = cari_linear(self.dompet.riwayat, "transportasi",
                            lambda t: t.deskripsi, lambda t: t.kategori)
        self.assertEqual(len(hasil), 1)

    def test_baca_angka_membedakan_format_salah(self):
        self.assertEqual(baca_angka(" 150000 "), 150000.0)
        self.assertEqual(baca_angka("-5"), -5.0)            # nilai negatif tetap angka
        for buruk in ("abc", "", "nan", "inf"):
            with self.assertRaises(FormatAngkaError):
                baca_angka(buruk)

    def test_banyak_goals_tersimpan_dan_dimuat(self):
        self.dompet.tambah_goals(Goals("Laptop", 5000000))
        self.dompet.tambah_goals(Goals("Liburan", 100000))
        self.dompet.tambah_goals(Goals("Buku", 20000))
        self.assertEqual(len(self.dompet.goals), 3)
        baru = Dompet(RiwayatFile(self.path))
        self.assertTrue(baru.muat_dari_file())
        self.assertEqual([g.nama for g in baru.goals], ["Laptop", "Liburan", "Buku"])

    def test_goals_nama_kembar_ditolak(self):
        self.dompet.tambah_goals(Goals("Laptop", 5000000))
        with self.assertRaises(ValueError):
            self.dompet.tambah_goals(Goals("  laptop ", 1000))
        self.assertEqual(len(self.dompet.goals), 1)

    def test_progres_tiap_goals_terhadap_saldo(self):
        self.dompet.tambah_goals(Goals("Besar", 70000))     # saldo 35000 -> 50%
        self.dompet.tambah_goals(Goals("Kecil", 20000))     # saldo 35000 -> 100%
        persen = {g.nama: g.hitung_persen(self.dompet.saldo) for g in self.dompet.goals}
        self.assertEqual(persen, {"Besar": 50.0, "Kecil": 100.0})
        self.assertEqual(self.dompet.goals_tercapai(), ["Kecil"])

    def test_cari_goals_dan_baris_goal_lama_mengubah_target(self):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("2026-11-01 08:00:00,GOAL,-,1000.0,Liburan\n")
            f.write("2026-11-02 08:00:00,GOAL,-,2500.0,liburan\n")   # nama sama -> ubah target
        baru = Dompet(RiwayatFile(self.path))
        baru.muat_dari_file()
        self.assertEqual(len(baru.goals), 1)
        self.assertEqual(baru.cari_goals("LIBURAN").target, 2500.0)
        self.assertIsNone(baru.cari_goals("tidak ada"))


if __name__ == "__main__":
    unittest.main()
