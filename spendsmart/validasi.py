"""Modul validasi input.

Semua fungsi di sini memakai `raise ValueError` supaya lapisan UI cukup
menangkap ValueError dan menampilkannya sebagai pesan, tanpa aplikasi crash.
"""
import math


def wajib_isi(**kolom):
    """Pastikan semua kolom terisi (memakai **kwargs).

    Contoh: wajib_isi(Deskripsi="makan", Nominal="")  -> ValueError.
    """
    kosong = [nama for nama, nilai in kolom.items() if not str(nilai or "").strip()]
    if kosong:
        raise ValueError("Kolom wajib diisi: " + ", ".join(kosong))


class FormatAngkaError(ValueError):
    """Dilempar bila teks bukan angka biasa (huruf, kosong, NaN, Infinity)."""


def baca_angka(teks):
    """Ubah teks menjadi float; raise FormatAngkaError bila bukan angka biasa."""
    try:
        nilai = float(str(teks).strip())
    except ValueError:
        raise FormatAngkaError("Input harus berupa angka.")
    if math.isnan(nilai) or math.isinf(nilai):
        raise FormatAngkaError("Input harus berupa angka biasa.")
    return nilai


def baca_nominal(teks, nama="Nominal", boleh_nol=False):
    """Ubah teks menjadi angka nominal; tolak bukan angka dan nilai tidak valid."""
    try:
        nilai = baca_angka(teks)
    except FormatAngkaError:
        raise FormatAngkaError(f"{nama} harus berupa angka (contoh: 25000, tanpa titik/koma).")
    if nilai < 0 or (nilai == 0 and not boleh_nol):
        batas = "negatif" if boleh_nol else "nol atau negatif"
        raise ValueError(f"{nama} tidak boleh {batas}.")
    return nilai
