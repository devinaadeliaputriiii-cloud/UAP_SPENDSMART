# SpendSmart - UAP_SPENDSMART

Aplikasi pencatat keuangan + target tabungan (tema data: riwayat transaksi keuangan).

## Struktur
```
UAP_SPENDSMART/
├── spendsmart/
│   ├── __init__.py
│   ├── fileio.py        # baca/tulis file dengan with open()  (r, a, w)
│   ├── processing.py    # Merge Sort, Linear/Binary Search, filter(**kwargs), total(*args), class Dompet
│   ├── validasi.py      # validasi input: raise ValueError
│   ├── models.py        # class Transaksi, Pemasukan, Pengeluaran, Goals, enum Kategori
│   └── testing.py       # unittest (25 uji)
├── daftar_transaksi.txt # data tabular (CSV): waktu,jenis,kategori,nominal,keterangan
├── main_cli.py          # antarmuka terminal (menu while True)
└── main_gui.py          # antarmuka GUI Tkinter (tampilan mengikuti App.java)
```

## Cara menjalankan
- CLI : `python main_cli.py`
- GUI : `python main_gui.py`
- Test: `python -m unittest spendsmart.testing -v`

## Tabel Refactoring
| No | Sebelum | Sesudah | Alasan |
|---|---|---|---|
| 1 | Pengurutan memakai `sorted()` / belum ada | `merge_sort` manual dengan decorate (key dihitung sekali per elemen) | O(n log n), stabil, tidak menghitung ulang key |
| 2 | Pencarian hanya linear untuk semua input | `cari_transaksi` memilih Binary Search untuk angka (nominal), Linear Search untuk teks | Binary search O(log n) untuk nominal tepat |
| 3 | Pengecekan input tersebar di handler tombol UI | Dipusatkan di `validasi.py` (`wajib_isi`, `baca_nominal`) | Tanpa duplikasi, mudah diuji tanpa UI |
| 4 | `catatPengeluaran` mengembalikan `False` bila saldo kurang | Melempar `SaldoTidakCukupError` | Error eksplisit dan tidak bisa terabaikan |
| 5 | Perulangan manual untuk total per kategori (di GUI dan CLI) | `Dompet.ringkasan_kategori()`, `filter_transaksi(**kriteria)`, `hitung_total(*args)` | Satu sumber logika dipakai CLI dan GUI |

## Kesesuaian GUI dengan versi Java (App.java)
Sama: ukuran jendela (480x380 dan 960x650), warna, halaman awal, kartu Status Goals,
Catat Transaksi, Batas Pengeluaran Harian, Riwayat Aktivitas (filter kategori),
Ringkasan, teks petunjuk di kolom isian, dan seluruh teks dialog.
Beda (kebutuhan UAS): riwayat berupa tabel (bukan TextArea) dengan kolom Cari dan
pengurutan lewat klik judul kolom.

## Banyak Goals
- Pengguna bisa membuat goals sebanyak yang diinginkan (GUI: tombol "+ Tambah Goals", CLI: menu 9).
- Nama goals tidak boleh kembar (tidak peka huruf besar/kecil).
- Setiap goals dihitung progresnya terhadap saldo yang sama. Kartu Status Goals menampilkan
  satu goals aktif (dipilih lewat dropdown) dan ringkasan persentase semua goals.
- Setiap goals disimpan sebagai satu baris `GOAL` di file, sehingga tetap ada setelah aplikasi ditutup.
