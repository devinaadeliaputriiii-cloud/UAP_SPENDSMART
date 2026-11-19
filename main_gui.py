"""Antarmuka GUI (Tkinter) SpendSmart. Jalankan: python main_gui.py

Tampilan mengikuti versi JavaFX (App.java): halaman awal, kartu Status Goals,
Catat Transaksi, Batas Pengeluaran Harian, Riwayat Aktivitas, dan Ringkasan.
Tambahan khusus UAS: riwayat berupa tabel dengan kolom pencarian dan pengurutan.
"""
import tkinter as tk
from tkinter import messagebox, ttk

from spendsmart.fileio import RiwayatFile
from spendsmart.models import DAFTAR_KATEGORI, Goals, rupiah
from spendsmart.processing import (Dompet, SaldoTidakCukupError, cari_transaksi,
                                   filter_transaksi, urutkan_transaksi)
from spendsmart.validasi import FormatAngkaError, baca_angka

# Palet warna yang sama dengan App.java
LATAR, AKSEN, KELUAR = "#F6F3EC", "#3E7B5A", "#B5654A"
TEKS, REDUP, GARIS = "#2F2F2F", "#6B6B6B", "#DDD8CC"
PROMPT_KATEGORI = "Pilih kategori"

# kolom tabel riwayat: (id, judul, lebar)
KOLOM = [("waktu", "Waktu", 105), ("jenis", "Jenis", 85), ("kategori", "Kategori", 85),
         ("deskripsi", "Deskripsi", 120), ("nominal", "Nominal", 85)]


def font(ukuran, tebal=False, miring=False):
    """Font dalam piksel (ukuran negatif = piksel), seperti -fx-font-size di JavaFX."""
    gaya = [g for g, aktif in (("bold", tebal), ("italic", miring)) if aktif]
    return ("Segoe UI", -ukuran, " ".join(gaya)) if gaya else ("Segoe UI", -ukuran)


class EntriPrompt(tk.Entry):
    """Kolom isian dengan teks petunjuk abu-abu (padanan setPromptText di JavaFX)."""

    def __init__(self, induk, petunjuk, lebar=30):
        super().__init__(induk, width=lebar, relief="solid", bd=1, highlightthickness=0)
        self.petunjuk, self.kosong = petunjuk, True
        self.bind("<FocusIn>", self._fokus_masuk)
        self.bind("<FocusOut>", self._fokus_keluar)
        self._tampilkan_petunjuk()

    def _tampilkan_petunjuk(self):
        super().delete(0, "end")
        super().insert(0, self.petunjuk)
        self.config(fg=REDUP)
        self.kosong = True

    def _fokus_masuk(self, _event=None):
        if self.kosong:
            super().delete(0, "end")
            self.config(fg=TEKS)
            self.kosong = False

    def _fokus_keluar(self, _event=None):
        if not super().get():
            self._tampilkan_petunjuk()

    def get(self):
        """Isi kolom; string kosong bila yang tampil hanya petunjuk."""
        return "" if self.kosong else super().get()

    def bersihkan(self):
        """Kosongkan isian dan tampilkan kembali petunjuk."""
        self._tampilkan_petunjuk()
        if self.focus_displayof() is self:
            self._fokus_masuk()


class AplikasiSpendSmart:
    """Kelas UI utama. Semua logika data didelegasikan ke objek Dompet."""

    def __init__(self, root, dompet):
        self.root, self.dompet = root, dompet
        self.kolom_urut, self.turun = "waktu", True    # default: terbaru di atas, seperti Java
        self.frame = None
        root.title("SpendSmart")
        root.configure(bg=LATAR)
        gaya = ttk.Style()
        gaya.theme_use("clam")
        gaya.configure("TProgressbar", background=AKSEN, troughcolor="#E6E2D8",
                       bordercolor=GARIS, lightcolor=AKSEN, darkcolor=AKSEN)
        gaya.configure("Treeview", rowheight=22)
        if not dompet.goals:
            self.halaman_awal()
        else:
            self._tampilkan_utama()
        if dompet.baris_rusak:
            messagebox.showwarning("Data rusak", f"{dompet.baris_rusak} baris file dilewati.")

    # ---------- komponen bersama ----------
    def _ganti_halaman(self):
        if self.frame:
            self.frame.destroy()
        self.frame = tk.Frame(self.root, bg=LATAR)
        self.frame.pack(fill="both", expand=True)

    def _atur_jendela(self, lebar, tinggi):
        """Ukuran jendela seperti Scene Java, lalu diletakkan di tengah layar."""
        self.root.update_idletasks()
        lebar = max(lebar, self.root.winfo_reqwidth())
        tinggi = max(tinggi, self.root.winfo_reqheight())
        x = max((self.root.winfo_screenwidth() - lebar) // 2, 0)
        y = max((self.root.winfo_screenheight() - tinggi) // 2, 0)
        self.root.geometry(f"{lebar}x{tinggi}+{x}+{y}")

    def _kartu(self, induk, judul):
        """Kartu putih berbingkai tipis dengan judul hijau (padanan buatKartu)."""
        kartu = tk.Frame(induk, bg="white", highlightbackground=GARIS,
                         highlightthickness=1, padx=14, pady=14)
        tk.Label(kartu, text=judul, bg="white", fg=AKSEN,
                 font=font(14, True)).pack(anchor="w", pady=(0, 10))
        return kartu

    def _tombol(self, induk, teks, warna, perintah):
        return tk.Button(induk, text=teks, command=perintah, bg=warna, fg="white",
                         activebackground=warna, activeforeground="white", relief="flat",
                         bd=0, cursor="hand2", font=font(12, True), padx=16, pady=8)

    def _baris_isian(self, induk, label, baris, petunjuk, latar="white"):
        tk.Label(induk, text=label, bg=latar).grid(row=baris, column=0, sticky="w", pady=6)
        entri = EntriPrompt(induk, petunjuk)
        entri.grid(row=baris, column=1, padx=(10, 0), pady=6)
        return entri

    def _combo_kategori(self, induk):
        combo = ttk.Combobox(induk, values=DAFTAR_KATEGORI, state="readonly", width=28)
        combo.set(PROMPT_KATEGORI)
        return combo

    @staticmethod
    def _pilihan(combo):
        """Kategori terpilih, atau None bila masih menampilkan 'Pilih kategori'."""
        nilai = combo.get()
        return nilai if nilai in DAFTAR_KATEGORI else None

    @staticmethod
    def _peringatan(pesan, judul="Peringatan", induk=None):
        messagebox.showwarning(judul, pesan, **({"parent": induk} if induk else {}))

    @staticmethod
    def _angka(teks, subjek, contoh, induk=None):
        """Teks -> float. Bila bukan angka tampil dialog 'Kesalahan Format', return None."""
        try:
            return baca_angka(teks)
        except FormatAngkaError:
            messagebox.showerror("Kesalahan Format", f"{subjek} harus berupa angka! "
                                 f"Tulis tanpa titik atau koma (contoh: {contoh}).",
                                 **({"parent": induk} if induk else {}))
            return None

    # ---------- halaman awal ----------
    def halaman_awal(self):
        self._ganti_halaman()
        tengah = tk.Frame(self.frame, bg=LATAR)
        tengah.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(tengah, text="SpendSmart", bg=LATAR, fg=AKSEN,
                 font=font(28, True)).pack(pady=(0, 8))
        tk.Label(tengah, text="Atur saldo awal dan target tabunganmu untuk memulai.",
                 bg=LATAR, fg=REDUP).pack(pady=(0, 16))
        form = tk.Frame(tengah, bg=LATAR)
        form.pack(pady=(0, 16))
        e_saldo = self._baris_isian(form, "Saldo awal (Rp):", 0, "Contoh: 300000", LATAR)
        e_nama = self._baris_isian(form, "Nama target tabungan:", 1, "Contoh: Liburan", LATAR)
        e_target = self._baris_isian(form, "Nominal target (Rp):", 2, "Contoh: 1000000", LATAR)

        def mulai():
            s, nama, t = e_saldo.get().strip(), e_nama.get().strip(), e_target.get().strip()
            if not s or not nama or not t:
                return self._peringatan("Seluruh kolom wajib diisi!")
            saldo = self._angka(s, "Saldo dan target", "300000")
            target = self._angka(t, "Saldo dan target", "300000")
            if saldo is None or target is None:
                return
            if saldo < 0:
                return self._peringatan("Saldo awal tidak boleh negatif!")
            if target <= 0:
                return self._peringatan("Nominal target harus lebih dari 0!")
            self.dompet.tambah_goals(Goals(nama, target))
            if saldo > 0:
                self.dompet.tambah_pemasukan("Saldo awal", saldo)
            self._tampilkan_utama()
            messagebox.showinfo("Berhasil", "Pengaturan awal tersimpan. Selamat menabung!")

        self._tombol(tengah, "Mulai", AKSEN, mulai).pack()
        self._atur_jendela(480, 380)

    # ---------- halaman utama ----------
    def _tampilkan_utama(self):
        self.halaman_utama()
        self.perbarui()
        self._atur_jendela(960, 650)

    def halaman_utama(self):
        self._ganti_halaman()
        self.frame.configure(padx=16, pady=16)

        # kartu Status Goals (lebar penuh) - mendukung banyak goals
        status = self._kartu(self.frame, "Status Goals")
        status.pack(fill="x")
        atas = tk.Frame(status, bg="white")
        atas.pack(fill="x")
        self.lbl_saldo = tk.Label(atas, bg="white", fg=TEKS, font=font(20, True))
        self.lbl_saldo.pack(side="left", padx=(0, 30))
        self.lbl_goals = tk.Label(atas, bg="white", fg=TEKS)
        self.lbl_goals.pack(side="left")
        self._tombol(atas, "+ Tambah Goals", AKSEN, self.dialog_goals).pack(side="right")
        self.c_goals = ttk.Combobox(atas, state="readonly", width=18)
        self.c_goals.pack(side="right", padx=10)
        self.c_goals.bind("<<ComboboxSelected>>", lambda e: self.perbarui())
        tk.Label(atas, text="Goals aktif:", bg="white").pack(side="right")
        self.bar = ttk.Progressbar(status, maximum=100, mode="determinate")
        self.bar.pack(fill="x", pady=10)
        bawah = tk.Frame(status, bg="white")
        bawah.pack(fill="x")
        self.lbl_progres = tk.Label(bawah, bg="white", fg=TEKS)
        self.lbl_progres.pack(side="left", padx=(0, 20))
        self.lbl_motivasi = tk.Label(bawah, bg="white", fg=AKSEN, font=font(12, miring=True))
        self.lbl_motivasi.pack(side="left")
        self.lbl_semua = tk.Label(status, bg="white", fg=REDUP, anchor="w")
        self.lbl_semua.pack(fill="x", pady=(6, 0))

        isi = tk.Frame(self.frame, bg=LATAR)
        isi.pack(fill="both", expand=True, pady=(14, 0))
        kiri = tk.Frame(isi, bg=LATAR)
        kiri.pack(side="left", fill="y", padx=(0, 14))
        kanan = tk.Frame(isi, bg=LATAR)
        kanan.pack(side="left", fill="both", expand=True)

        # kartu Catat Transaksi
        k = self._kartu(kiri, "Catat Transaksi")
        k.pack(fill="x", pady=(0, 14))
        form = tk.Frame(k, bg="white")
        form.pack(anchor="w")
        self.e_desk = self._baris_isian(form, "Deskripsi", 0, "Contoh: Makan siang")
        self.e_nominal = self._baris_isian(form, "Nominal (Rp)", 1, "Contoh: 25000")
        tk.Label(form, text="Kategori", bg="white").grid(row=2, column=0, sticky="w", pady=6)
        self.c_kat = self._combo_kategori(form)
        self.c_kat.grid(row=2, column=1, padx=(10, 0), pady=6, sticky="w")
        tombol = tk.Frame(k, bg="white")
        tombol.pack(anchor="w", pady=(10, 0))
        self._tombol(tombol, "Tambah Tabungan", AKSEN, self.tambah_tabungan).pack(side="left")
        self._tombol(tombol, "Catat Pengeluaran", KELUAR,
                     self.catat_pengeluaran).pack(side="left", padx=(10, 0))

        # kartu Batas Pengeluaran Harian
        k = self._kartu(kiri, "Batas Pengeluaran Harian")
        k.pack(fill="x")
        form = tk.Frame(k, bg="white")
        form.pack(anchor="w")
        tk.Label(form, text="Kategori", bg="white").grid(row=0, column=0, sticky="w", pady=6)
        self.c_batas = self._combo_kategori(form)
        self.c_batas.grid(row=0, column=1, padx=(10, 0), pady=6, sticky="w")
        self.e_batas = self._baris_isian(form, "Batas per hari (Rp)", 1, "Contoh: 200000")
        self._tombol(k, "Atur Batas Harian", AKSEN, self.atur_batas).pack(anchor="w", pady=(10, 0))

        # kartu Riwayat Aktivitas (tabel + filter + cari + urut)
        k = self._kartu(kanan, "Riwayat Aktivitas")
        k.pack(fill="both", expand=True, pady=(0, 14))
        filter_ = tk.Frame(k, bg="white")
        filter_.pack(fill="x", pady=(0, 10))
        tk.Label(filter_, text="Filter kategori:", bg="white").pack(side="left")
        self.c_filter = ttk.Combobox(filter_, values=["Semua"] + DAFTAR_KATEGORI,
                                     state="readonly", width=13)
        self.c_filter.set("Semua")
        self.c_filter.pack(side="left", padx=(10, 16))
        self.c_filter.bind("<<ComboboxSelected>>", lambda e: self.perbarui_tabel())
        tk.Label(filter_, text="Cari:", bg="white").pack(side="left")
        self.e_cari = EntriPrompt(filter_, "kata kunci / nominal", lebar=18)
        self.e_cari.pack(side="left", padx=(10, 0))
        self.e_cari.bind("<KeyRelease>", lambda e: self.perbarui_tabel())

        area = tk.Frame(k, bg="white")
        area.pack(fill="both", expand=True)
        self.tabel = ttk.Treeview(area, columns=[c for c, _, _ in KOLOM],
                                  show="headings", height=5)
        for kode, judul, lebar in KOLOM:
            self.tabel.heading(kode, text=judul, command=lambda c=kode: self.urut_kolom(c))
            self.tabel.column(kode, width=lebar, anchor="e" if kode == "nominal" else "w")
        self.tabel.tag_configure("PEMASUKAN", foreground=AKSEN)
        self.tabel.tag_configure("PENGELUARAN", foreground=KELUAR)
        scroll = ttk.Scrollbar(area, command=self.tabel.yview)
        self.tabel.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tabel.pack(side="left", fill="both", expand=True)
        self.lbl_info = tk.Label(k, bg="white", fg=REDUP, anchor="w")
        self.lbl_info.pack(fill="x", pady=(6, 0))

        # kartu Ringkasan
        k = self._kartu(kanan, "Ringkasan Pengeluaran (total dan hari ini)")
        k.pack(fill="x")
        self.lbl_ringkasan = tk.Label(k, bg="white", fg=TEKS, justify="left",
                                      anchor="w", wraplength=440)
        self.lbl_ringkasan.pack(fill="x")

    # ---------- tambah goals baru ----------
    def dialog_goals(self):
        """Jendela kecil untuk membuat goals tambahan."""
        win = tk.Toplevel(self.root)
        win.title("Tambah Goals")
        win.configure(bg=LATAR)
        win.resizable(False, False)
        win.transient(self.root)
        form = tk.Frame(win, bg=LATAR, padx=24, pady=20)
        form.pack()
        tk.Label(form, text="Tambah Goals Baru", bg=LATAR, fg=AKSEN,
                 font=font(18, True)).grid(row=0, column=0, columnspan=2, pady=(0, 12))
        e_nama = self._baris_isian(form, "Nama target:", 1, "Contoh: Liburan", LATAR)
        e_target = self._baris_isian(form, "Nominal target (Rp):", 2, "Contoh: 1000000", LATAR)

        def simpan():
            nama, teks = e_nama.get().strip(), e_target.get().strip()
            if not nama or not teks:
                return self._peringatan("Seluruh kolom wajib diisi!", induk=win)
            target = self._angka(teks, "Nominal target", "1000000", win)
            if target is None:
                return
            if target <= 0:
                return self._peringatan("Nominal target harus lebih dari 0!", induk=win)
            try:
                self.dompet.tambah_goals(Goals(nama, target))
            except ValueError as err:           # nama kembar
                return self._peringatan(str(err), induk=win)
            win.destroy()
            self.c_goals.set(nama)              # goals baru langsung jadi yang aktif
            self.perbarui()
            messagebox.showinfo("Berhasil", f"Goals {nama} ditambahkan.")

        self._tombol(form, "Simpan Goals", AKSEN, simpan).grid(row=3, column=0, columnspan=2,
                                                               pady=(12, 0))
        win.grab_set()

    # ---------- aksi tombol (pesan sama dengan App.java) ----------
    def _bersihkan_form(self):
        self.e_desk.bersihkan()
        self.e_nominal.bersihkan()
        self.c_kat.set(PROMPT_KATEGORI)
        self.e_desk.focus_set()

    def tambah_tabungan(self):
        deskripsi, teks = self.e_desk.get().strip(), self.e_nominal.get().strip()
        if not teks:
            return self._peringatan("Kolom nominal wajib diisi!")
        nominal = self._angka(teks, "Nominal", "150000")
        if nominal is None:
            return
        if nominal <= 0:
            return self._peringatan("Nominal harus lebih dari 0!")
        tercapai_lama = set(self.dompet.goals_tercapai())
        self.dompet.tambah_pemasukan(deskripsi or "Tabungan", nominal)
        self._bersihkan_form()
        self.perbarui()
        pesan = f"Tabungan {rupiah(nominal)} berhasil ditambahkan."
        baru = [n for n in self.dompet.goals_tercapai() if n not in tercapai_lama]
        if baru and len(self.dompet.goals) == 1:
            pesan += "\n\nSelamat! Target tabunganmu sudah tercapai!"
        elif baru:
            pesan += "\n\nSelamat! Target tercapai: " + ", ".join(baru) + "!"
        messagebox.showinfo("Berhasil", pesan)

    def catat_pengeluaran(self):
        deskripsi, teks = self.e_desk.get().strip(), self.e_nominal.get().strip()
        kategori = self._pilihan(self.c_kat)
        if not deskripsi or not teks or kategori is None:
            return self._peringatan("Deskripsi, nominal, dan kategori wajib diisi!")
        nominal = self._angka(teks, "Nominal", "25000")
        if nominal is None:
            return
        if nominal <= 0:
            return self._peringatan("Nominal harus lebih dari 0!")
        try:
            self.dompet.catat_pengeluaran(deskripsi, nominal, kategori)
        except SaldoTidakCukupError as err:
            return self._peringatan(str(err), "Saldo Tidak Cukup")
        self._bersihkan_form()
        self.perbarui()
        pengingat = self.dompet.cek_batas(kategori)
        if pengingat:
            self._peringatan(pengingat, "Pengingat Anggaran")
        else:
            messagebox.showinfo("Berhasil", f"Pengeluaran {rupiah(nominal)} untuk {kategori} tercatat.")

    def atur_batas(self):
        kategori, teks = self._pilihan(self.c_batas), self.e_batas.get().strip()
        if kategori is None or not teks:
            return self._peringatan("Kategori dan batas harian wajib diisi!")
        batas = self._angka(teks, "Batas harian", "200000")
        if batas is None:
            return
        if batas <= 0:
            return self._peringatan("Batas harian harus lebih dari 0!")
        self.dompet.atur_batas(kategori, batas)
        self.e_batas.bersihkan()
        self.perbarui()
        pengingat = self.dompet.cek_batas(kategori)
        if pengingat:
            self._peringatan(pengingat, "Pengingat Anggaran")
        else:
            messagebox.showinfo("Berhasil", f"Batas harian {kategori} diatur menjadi "
                                f"{rupiah(batas)} per hari.")

    # ---------- tabel: filter -> cari -> urut ----------
    def urut_kolom(self, kolom):
        """Klik judul kolom: kolom sama -> balik arah; kolom baru -> mulai menaik."""
        self.turun = not self.turun if kolom == self.kolom_urut else False
        self.kolom_urut = kolom
        self.perbarui_tabel()

    def _data_tampil(self):
        pilihan = self.c_filter.get()
        if pilihan in DAFTAR_KATEGORI:      # sama dengan Java: filter kategori = pengeluaran
            data = filter_transaksi(self.dompet.riwayat, jenis="PENGELUARAN", kategori=pilihan)
        else:
            data = self.dompet.riwayat
        data = cari_transaksi(data, self.e_cari.get())
        return urutkan_transaksi(data, self.kolom_urut, self.turun)

    def perbarui_tabel(self):
        self.tabel.delete(*self.tabel.get_children())
        data = self._data_tampil()
        for t in data:
            self.tabel.insert("", "end", tags=(t.jenis,), values=(
                t.waktu_teks, t.jenis, t.kategori, t.deskripsi, rupiah(t.nominal)))
        panah = "  ▼" if self.turun else "  ▲"
        for kode, judul, _ in KOLOM:
            self.tabel.heading(kode, text=judul + (panah if kode == self.kolom_urut else ""))
        if not self.dompet.riwayat:
            self.lbl_info.config(text="Belum ada riwayat.")
        elif not data:
            self.lbl_info.config(text="Tidak ada data yang cocok.")
        else:
            self.lbl_info.config(text=f"{len(data)} baris - klik judul kolom untuk mengurutkan")

    # ---------- segarkan seluruh tampilan ----------
    def perbarui(self):
        d = self.dompet
        saldo = d.saldo
        nama_goals = [g.nama for g in d.goals]
        self.c_goals.config(values=nama_goals)
        if self.c_goals.get() not in nama_goals:
            self.c_goals.set(nama_goals[0])
        g = d.cari_goals(self.c_goals.get())
        persen = g.hitung_persen(saldo)
        self.lbl_saldo.config(text="Saldo: " + rupiah(saldo))
        self.lbl_goals.config(text=f"Goals: {g.nama} (target {rupiah(g.target)})")
        self.bar["value"] = persen
        self.lbl_progres.config(text=f"Progres {persen:.1f}%  |  Sisa {rupiah(g.hitung_sisa(saldo))}")
        self.lbl_motivasi.config(text=g.pesan_motivasi(saldo))
        self.lbl_semua.config(text="Semua goals: " + "  |  ".join(
            f"{x.nama} {x.hitung_persen(saldo):.0f}%" + (" ✓" if saldo >= x.target else "")
            for x in d.goals))
        self.perbarui_tabel()

        totals, total_semua, besar = d.ringkasan_kategori()
        baris = []
        for nama in DAFTAR_KATEGORI:
            teks = f"{nama}: {rupiah(totals[nama])}   | hari ini {rupiah(d.total_pengeluaran(nama, True))}"
            if nama in d.batas:
                teks += f" / batas harian {rupiah(d.batas[nama])}"
            baris.append(teks)
        baris.append(f"\nTotal pengeluaran: {rupiah(total_semua)}")
        if besar is None:
            baris.append("Belum ada pengeluaran.")
        else:
            baris.append(f"Kategori terbesar: {besar} ({totals[besar] / total_semua * 100:.0f}% dari total)")
        self.lbl_ringkasan.config(text="\n".join(baris))


def main():
    """Muat data lama (jika ada) lalu jalankan jendela GUI."""
    dompet = Dompet(RiwayatFile("daftar_transaksi.txt"))
    dompet.muat_dari_file()
    root = tk.Tk()
    AplikasiSpendSmart(root, dompet)
    root.mainloop()


if __name__ == "__main__":
    main()
