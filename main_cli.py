"""Antarmuka CLI (terminal) SpendSmart. Jalankan: python main_cli.py"""
from spendsmart.fileio import RiwayatFile
from spendsmart.models import DAFTAR_KATEGORI, Goals, rupiah
from spendsmart.processing import (Dompet, cari_transaksi, filter_transaksi,
                                   urutkan_transaksi)
from spendsmart.validasi import baca_nominal, wajib_isi

FILE_DATA = "daftar_transaksi.txt"
KOLOM = ["waktu", "jenis", "kategori", "deskripsi", "nominal"]

MENU = """
===== MENU SPENDSMART =====
1. Lihat semua riwayat
2. Filter berdasarkan kategori
3. Cari kata kunci / nominal
4. Urutkan riwayat
5. Tambah tabungan
6. Catat pengeluaran
7. Atur batas harian
8. Ringkasan pengeluaran
9. Tambah goals baru
0. Keluar"""


def tampil_tabel(data):
    """Cetak daftar transaksi sebagai tabel teks."""
    if not data:
        print("(tidak ada data)")
        return
    print(f"{'No':<4}{'Waktu':<18}{'Jenis':<13}{'Kategori':<14}{'Deskripsi':<24}{'Nominal':>14}")
    print("-" * 87)
    for no, t in enumerate(data, 1):
        print(f"{no:<4}{t.waktu_teks:<18}{t.jenis:<13}{t.kategori:<14}"
              f"{t.deskripsi[:22]:<24}{rupiah(t.nominal):>14}")
    print(f"({len(data)} baris)")


def pilih_dari_daftar(judul, pilihan):
    """Tampilkan pilihan bernomor, kembalikan item terpilih (ValueError bila salah)."""
    print(judul)
    for i, nama in enumerate(pilihan, 1):
        print(f"  {i}. {nama}")
    try:
        nomor = int(input("Pilih nomor: "))
    except ValueError:
        raise ValueError("Pilihan harus berupa angka.")
    if not 1 <= nomor <= len(pilihan):
        raise ValueError("Nomor pilihan di luar daftar.")
    return pilihan[nomor - 1]


def setup_awal(dompet):
    """Pengaturan pertama kali: saldo awal dan goals. Ulangi sampai input valid."""
    print("Selamat datang di SpendSmart! Atur saldo awal dan target tabungan.")
    while True:
        try:
            saldo_txt, nama = input("Saldo awal (Rp): "), input("Nama target tabungan: ")
            target_txt = input("Nominal target (Rp): ")
            wajib_isi(Saldo=saldo_txt, Nama=nama, Target=target_txt)
            saldo = baca_nominal(saldo_txt, "Saldo awal", boleh_nol=True)
            dompet.tambah_goals(Goals(nama, baca_nominal(target_txt, "Target")))
            if saldo > 0:
                dompet.tambah_pemasukan("Saldo awal", saldo)
            return
        except ValueError as err:
            print("Peringatan:", err)


def tampil_status(dompet):
    """Cetak saldo dan progres SEMUA goals."""
    saldo = dompet.saldo
    print(f"\nSaldo: {rupiah(saldo)}")
    for no, g in enumerate(dompet.goals, 1):
        persen = g.hitung_persen(saldo)
        print(f"  Goals {no}: {g.nama} ({rupiah(g.target)}) | {persen:.1f}% | Sisa {rupiah(g.hitung_sisa(saldo))}")
    for g in dompet.goals:
        if g.hitung_persen(saldo) < 100:
            print(f"{g.nama}: {g.pesan_motivasi(saldo)}")


def menu_lihat(dompet):
    tampil_tabel(urutkan_transaksi(dompet.riwayat, "waktu", turun=True))


def menu_filter(dompet):
    kat = pilih_dari_daftar("Kategori:", DAFTAR_KATEGORI)
    tampil_tabel(filter_transaksi(dompet.riwayat, kategori=kat))


def menu_cari(dompet):
    kata = input("Kata kunci (teks) atau nominal tepat (angka): ")
    tampil_tabel(cari_transaksi(dompet.riwayat, kata))


def menu_urut(dompet):
    kolom = pilih_dari_daftar("Urutkan berdasarkan:", KOLOM)
    arah = pilih_dari_daftar("Arah:", ["Menaik (kecil -> besar)", "Menurun (besar -> kecil)"])
    tampil_tabel(urutkan_transaksi(dompet.riwayat, kolom, turun=arah.startswith("Menurun")))


def menu_tabung(dompet):
    desk = input("Deskripsi: ")
    wajib_isi(Deskripsi=desk)
    dompet.tambah_pemasukan(desk, baca_nominal(input("Nominal (Rp): ")))
    print("Tabungan tercatat.")


def menu_keluar(dompet):
    desk = input("Deskripsi: ")
    wajib_isi(Deskripsi=desk)
    nominal = baca_nominal(input("Nominal (Rp): "))
    kat = pilih_dari_daftar("Kategori:", DAFTAR_KATEGORI)
    dompet.catat_pengeluaran(desk, nominal, kat)
    print("Pengeluaran tercatat.")
    pesan = dompet.cek_batas(kat)
    if pesan:
        print(pesan)


def menu_batas(dompet):
    kat = pilih_dari_daftar("Kategori:", DAFTAR_KATEGORI)
    dompet.atur_batas(kat, baca_nominal(input("Batas harian (Rp): "), "Batas harian"))
    print(f"Batas harian {kat} tersimpan.")


def menu_goals(dompet):
    """Tambah goals baru (nama tidak boleh kembar)."""
    nama = input("Nama target: ")
    wajib_isi(Nama=nama)
    dompet.tambah_goals(Goals(nama, baca_nominal(input("Nominal target (Rp): "), "Target")))
    print(f"Goals {nama.strip()} ditambahkan.")


def menu_ringkasan(dompet):
    totals, total_semua, besar = dompet.ringkasan_kategori()
    for nama, total in totals.items():
        print(f"{nama:<14}{rupiah(total):>14}   hari ini {rupiah(dompet.total_pengeluaran(nama, True))}")
    print(f"Total pengeluaran: {rupiah(total_semua)}")
    print(f"Terbesar: {besar}" if besar else "Belum ada pengeluaran.")


def main():
    """Loop menu utama; ValueError ditangkap agar program tidak crash."""
    dompet = Dompet(RiwayatFile(FILE_DATA))
    if not dompet.muat_dari_file():
        setup_awal(dompet)
    if dompet.baris_rusak:
        print(f"Catatan: {dompet.baris_rusak} baris file rusak dilewati.")
    aksi = {"1": menu_lihat, "2": menu_filter, "3": menu_cari, "4": menu_urut,
            "5": menu_tabung, "6": menu_keluar, "7": menu_batas, "8": menu_ringkasan, "9": menu_goals}
    while True:
        tampil_status(dompet)
        print(MENU)
        pilihan = input("Pilih menu: ").strip()
        if pilihan == "0":
            print("Sampai jumpa!")
            break
        fungsi = aksi.get(pilihan)
        if fungsi is None:
            print("Menu tidak dikenal.")
            continue
        try:
            fungsi(dompet)
        except ValueError as err:
            print("Peringatan:", err)


if __name__ == "__main__":
    main()
