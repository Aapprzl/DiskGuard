# DiskGuard v1.0.0

Desktop tool untuk Windows 11 untuk Recovery Data dan Health Check SSD/HDD.

![DiskGuard](icon.png)

## Instalasi

1. Pastikan Python 3.10+ terinstall
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Cara Menjalankan

### Via Python
```bash
python main.py
```

### Via Executable
```
dist/DiskGuard.exe
```

**Catatan:** Aplikasi akan otomatis meminta akses Administrator (UAC popup) saat dibuka.

## Fitur

### 1. Recovery Tab
- Scan drive untuk file berdasarkan kategori (Documents, Images, Videos, Audio, Archives)
- Tree view untuk navigasi folder
- Filter dan search filename
- Auto-sort: File Error (0 B) muncul di atas dan tidak tercentang
- Readable files otomatis tercentang saat pertama muncul
- Byte-level recovery dengan tolerance bad sector
- Timeout handling - file yang timeout tetap diproses dan tidak menghentikan operasi
- Progress tracking real-time dengan counter
- Live log dengan color coding:
  - `[OK]` - Hijau (file berhasil di-rescue)
  - `[PARTIAL]` - Kuning (file berhasil sebagian)
  - `[FAILED]` - Merah (file gagal)
  - `[INFO]` - Biru (informasi)
- Report popup di akhir operasi

### 2. Health Check Tab
- Deteksi semua disk yang terinstall
- Baca SMART data (status, suhu, bad sectors, dll)
- Tampilkan penggunaan disk (used/free)
- Color coding: hijau (Good), kuning (Warning), merah (Critical)
- Progress bar untuk health score

## Konfigurasi

Settings disimpan di `~/.diskguard/config.json`:
- `default_output_folder`: Folder default untuk recovery
- `chunk_size_mb`: Ukuran chunk transfer (default: 4MB)
- `auto_retry_count`: Jumlah retry otomatis (default: 5)

## Struktur Project

```
diskguard/
├── main.py              # Entry point (dengan auto UAC elevation)
├── config.py            # Settings management
├── core/
│   ├── health.py        # SMART data, disk usage
│   └── recovery.py      # Data recovery engine
├── ui/
│   ├── app.py           # Main window
│   ├── tab_health.py    # Health check UI
│   └── tab_recovery.py  # Recovery UI
├── utils/
│   └── helpers.py       # Utility functions
├── icon.ico             # App icon
├── icon.png             # App icon (PNG)
├── run.bat              # Quick launch script
├── run_admin.bat        # Launch as Administrator
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

## Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon="icon.ico" --name="DiskGuard" \
  --collect-all customtkinter --collect-all psutil \
  --hidden-import=wmi --hidden-import=win32api \
  --hidden-import=win32com --hidden-import=win32com.client \
  main.py
```

Executable akan tersedia di folder `dist/DiskGuard.exe`

## Catatan

- Beberapa SMART attributes mungkin tidak tersedia di consumer SSD
- Aplikasi auto-request admin rights via UAC
- Jangan cabut drive saat proses rescue berlangsung
- File timeout akan ditandai sebagai "partial" dan tetap diproses
