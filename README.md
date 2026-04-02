# DiskGuard v1.0.0

Desktop tool untuk Windows 11 dengan 3 fitur utama: Recovery Data, Smart Transfer, dan Health Check SSD/HDD.

## Instalasi

1. Pastikan Python 3.10+ terinstall
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Cara Menjalankan

```
python main.py
```

**Penting:** Jalankan sebagai Administrator untuk akses penuh ke SMART data dan recovery.

## Fitur

### 1. Health Check
- Deteksi semua disk yang terinstall
- Baca SMART data (status, suhu, bad sectors, dll)
- Tampilkan penggunaan disk (used/free)
- Color coding: hijau (Good), kuning (Warning), merah (Critical)
- Progress bar untuk health score

### 2. Smart Transfer
- Copy file/folder dengan retry otomatis
- Pause/Resume/Cancel transfer
- Byte-level copy dengan chunk 4MB
- Progress real-time: persentase, kecepatan (MB/s), ETA
- Verifikasi ukuran file setelah copy
- Log aktivitas transfer
- Handle stalled transfer (retry jika speed=0 selama 10 detik)

### 3. Data Recovery
- Scan drive untuk file berdasarkan kategori
- Filter: Documents, Images, Videos, Audio, Archives
- Byte-level recovery dengan tolerance bad sector
- Isi chunk yang gagal dibaca dengan zeros
- Progress rescue dengan counter
- Report: sukses penuh, partial, gagal

## Konfigurasi

Settings disimpan di `~/.diskguard/config.json`:
- `default_output_folder`: Folder default untuk recovery
- `chunk_size_mb`: Ukuran chunk transfer (default: 4MB)
- `auto_retry_count`: Jumlah retry otomatis (default: 5)

## Struktur Project

```
diskguard/
├── main.py              # Entry point
├── config.py            # Settings management
├── core/
│   ├── health.py        # SMART data, disk usage
│   ├── recovery.py      # Data recovery engine
│   └── transfer.py      # Smart transfer engine
├── ui/
│   ├── app.py           # Main window
│   ├── tab_health.py    # Health check UI
│   ├── tab_recovery.py  # Recovery UI
│   └── tab_transfer.py  # Transfer UI
├── utils/
│   └── helpers.py       # Utility functions
└── requirements.txt
```

## Requirements

- Python 3.10+
- Windows 10/11
- customtkinter
- psutil
- wmi
- pywin32
- Pillow

## Catatan

- Beberapa SMART attributes mungkin tidak tersedia di consumer SSD
- Jalankan sebagai Administrator untuk data SMART lengkap
- Jangan cabut drive saat proses transfer/rescue berlangsung
