# Alya Telegram Bot v2.0

## Deskripsi
Bot Telegram Alya v2.0 dengan fitur keamanan enterprise-grade yang telah di-upgrade dari versi sebelumnya.

## Fitur Utama
- ✅ **Anti-spam System**: Deteksi pola spam, filter pesan duplikat, deteksi rapid messaging
- ✅ **Rate Limiting**: Pembatasan pesan per user dengan cooldown progresif
- ✅ **Sistem Keamanan**: Verifikasi user otomatis, manajemen sesi, tracking user mencurigakan
- ✅ **Moderasi Grup**: Warning otomatis, mute, ban berdasarkan spam score
- ✅ **Backup Otomatis**: Backup data dengan rotasi file setiap jam
- ✅ **Logging Komprehensif**: File log dan console logging dengan level detail

## File Struktur
```
├── main.py              # Entry point utama bot
├── config.py           # Konfigurasi sistem
├── bot_data.py         # Manajemen data dan statistik user
├── handlers.py         # Handler pesan dengan security check
├── anti_spam.py        # Sistem anti-spam
├── rate_limiter.py     # Rate limiting per user
├── security.py         # Sistem keamanan dan verifikasi
├── moderation.py       # Sistem moderasi grup
├── backup.py          # Sistem backup otomatis
├── utils.py           # Utility functions
└── replit.md          # Dokumentasi project
```

## Instalasi

1. Install dependencies:
```bash
pip install -r bot_requirements.txt
```
Atau manual:
```bash
pip install python-telegram-bot[job-queue]==20.8 requests
```

2. Set environment variable untuk token:
```bash
export TELEGRAM_TOKEN="your_bot_token_here"
```

3. Jalankan bot:
```bash
python main.py
```

## Perintah Bot

### Perintah Umum
- `/start` - Info bot dan status
- `/help` - Bantuan lengkap
- `/status` - Status pribadi user

### Perintah Admin
- `/on` - Aktifkan di grup
- `/off` - Nonaktifkan di grup  
- `/akses [ID]` - Beri akses user
- `/hapus_akses [ID]` - Cabut akses
- `/ban [ID] [HARI]` - Ban user
- `/unban [ID]` - Hapus ban
- `/mute [ID] [MENIT]` - Mute user di grup
- `/unmute [ID]` - Unmute user
- `/resetlimit [ID]` - Reset rate limit
- `/marksafe [ID]` - Tandai user aman
- `/changeid` - Ganti session ID
- `/backup` - Buat backup manual
- `/adminstatus` - Status lengkap admin

## Konfigurasi

Edit file `config.py` untuk menyesuaikan:
- Rate limiting thresholds
- Spam detection patterns
- Security settings
- Backup intervals

## Cara Penggunaan

### Di Grup
Mulai pesan dengan "Alya" diikuti pertanyaan:
```
Alya apa kabar hari ini?
```

### Private Chat
Langsung kirim pesan tanpa prefix:
```
Halo, bagaimana cuaca hari ini?
```

## Fitur Keamanan

### Anti-Spam
- Pattern detection untuk spam umum
- Filter link mencurigakan
- Deteksi pesan duplikat
- Analisis rapid messaging
- Progressive punishment system

### Rate Limiting
- 10 pesan per menit per user
- 100 pesan per jam per user
- 5 API calls per menit per user
- Cooldown progresif untuk violator

### Moderasi Otomatis
- Warning → Mute → Ban progression
- Score-based punishment
- Auto-cleanup expired restrictions
- Group-specific moderation logs

## Backup & Recovery
- Backup otomatis setiap jam
- Rotasi file backup (max 10 files)
- Manual backup via command
- Emergency backup sebelum operasi kritikal

## Troubleshooting

### Bot tidak merespon
1. Cek token Telegram valid
2. Pastikan API eksternal accessible
3. Periksa logs di `bot.log`

### Rate limit error
1. User mencapai limit pesan
2. Gunakan `/resetlimit [ID]` untuk reset
3. Adjust config rate limits jika perlu

### Spam detection false positive
1. Gunakan `/marksafe [ID]` untuk whitelist user
2. Adjust spam patterns di config
3. Reset spam data user

## Support
Hubungi admin bot untuk bantuan teknis dan konfigurasi lanjutan.

---
**Alya Bot v2.0** - Enhanced Security & Anti-Spam Protection