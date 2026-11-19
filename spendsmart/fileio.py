"""fileio: penyimpanan permanen ke file CSV (selalu memakai `with open()`).

Format baris: waktu,jenis,kategori,nominal,keterangan
Jenis: GOAL | BATAS | PEMASUKAN | PENGELUARAN
"""


class RiwayatFile:
    """Membaca & menulis riwayat transaksi ke file teks CSV."""

    def __init__(self, nama_file="riwayat.csv"):
        self.nama_file = nama_file

    def tulis(self, waktu, jenis, kategori, nominal, keterangan):
        """Tambah satu baris ke akhir file (mode 'a'). Return True bila berhasil."""
        bersih = str(keterangan).replace(",", " ").replace("\n", " ").strip()
        baris = f"{waktu},{jenis},{kategori},{nominal},{bersih}\n"
        try:
            with open(self.nama_file, "a", encoding="utf-8") as f:
                f.write(baris)
            return True
        except OSError as e:
            print("Gagal menyimpan ke file:", e)
            return False

    def baca_semua(self):
        """Baca semua baris valid (mode 'r'). File hilang -> list kosong."""
        hasil = []
        try:
            with open(self.nama_file, "r", encoding="utf-8") as f:
                for baris in f:
                    baris = baris.strip()
                    if not baris:
                        continue
                    bagian = baris.split(",", 4)
                    if len(bagian) == 5:
                        hasil.append(bagian)
        except FileNotFoundError:
            pass  # belum ada file = aplikasi baru pertama kali dijalankan
        except OSError as e:
            print("File riwayat tidak bisa dibaca:", e)
        return hasil

    def ekspor(self, nama_tujuan, daftar_transaksi):
        """Tulis ulang tabel yang sedang tampil ke file lain (mode 'w')."""
        with open(nama_tujuan, "w", encoding="utf-8") as f:
            f.write("waktu,jenis,kategori,nominal,keterangan\n")
            for t in daftar_transaksi:
                ket = t.deskripsi.replace(",", " ")
                f.write(f"{t.waktu_file},{t.jenis},{t.kategori},{t.nominal},{ket}\n")
