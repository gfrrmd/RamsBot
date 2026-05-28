# 🤖 RamsBot

Bot Telegram VIP berbasis **Telethon** yang memungkinkan user berlangganan dan menghubungkan akun Telegram mereka untuk menggunakan fitur-fitur eksklusif.

---

## ✨ Fitur

### 👤 User (VIP)
| Fitur | Deskripsi |
|---|---|
| `/setup` | Hubungkan akun Telegram ke bot (login via nomor HP + OTP) |
| Download media | Download media dari pesan Telegram |
| Copy pesan | Salin pesan dari channel/grup ke tempat lain |
| Story viewer | Lihat story Telegram secara anonim |
| Auto download | Download media view-once secara otomatis |
| Broadcast | Kirim pesan ke banyak grup/channel sekaligus |
| Ping | Cek latensi dan status koneksi session |

### 🛡️ Admin
| Fitur | Deskripsi |
|---|---|
| `/gift <user_id\|@username> [hari]` | Berikan VIP ke user |
| `/revoke <user_id\|@username>` | Cabut VIP dari user |
| Blacklist channel | Tambah/hapus channel dari daftar terlarang |
| Backup database | Backup data DB langsung via bot |
| Panel admin | Menu interaktif manajemen user VIP |

---

## 🗂️ Struktur Proyek

```
RamsBot/
├── main.py                  # Entry point, registrasi semua handler
├── config.py                # Konfigurasi dari environment variables
├── database.py              # Semua fungsi PostgreSQL
├── client_manager.py        # Manajemen Telethon client per user
├── keyboards.py             # Definisi tombol inline & reply keyboard
│
├── auth/
│   ├── setup.py             # ConversationHandler proses /setup
│   └── states.py            # State constants & temp_store
│
├── admin/
│   ├── callbacks.py         # Handler callback query admin
│   ├── gift.py              # Perintah /gift
│   ├── vip.py               # Perintah /revoke
│   ├── blacklist.py         # Manajemen blacklist channel
│   └── backup.py            # Fitur backup database
│
├── user/
│   ├── start.py             # /start, /cancel
│   ├── download.py          # Fitur download media
│   ├── copy.py              # Fitur copy pesan
│   ├── story.py             # Fitur story viewer
│   ├── auto_dl.py           # Fitur auto download view-once
│   ├── broadcast.py         # Fitur broadcast pesan
│   ├── ping.py              # Fitur ping/cek latensi
│   ├── subscription.py      # Info langganan VIP
│   ├── tasks.py             # Background tasks
│   └── callbacks.py         # Handler callback query user
│
└── utils/
    └── helpers.py           # Fungsi utilitas umum
```

---

## ⚙️ Environment Variables

Tambahkan variabel berikut di Railway (atau `.env` untuk lokal):

| Variable | Wajib | Keterangan |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token bot dari [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | ✅ | Telegram user ID admin |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `API_ID` | ✅ | API ID dari [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ | API Hash dari [my.telegram.org](https://my.telegram.org) |
| `RESTRICTED_CHANNELS` | ❌ | JSON array channel ID yang diblokir, contoh: `[-1001234, -1005678]` |

---

## 🚀 Deploy ke Railway

1. Fork atau push repo ini ke GitHub
2. Buat project baru di [Railway](https://railway.app)
3. Tambahkan **PostgreSQL** plugin di Railway
4. Set semua environment variables di atas
5. Deploy — Railway akan otomatis menjalankan `main.py`

### Jalankan Lokal

```bash
# Clone repo
git clone https://github.com/gfrrmd/RamsBot.git
cd RamsBot

# Install dependencies
pip install python-telegram-bot telethon psycopg2-binary

# Set environment variables
export BOT_TOKEN=...
export ADMIN_ID=...
export DATABASE_URL=...
export API_ID=...
export API_HASH=...

# Jalankan
python main.py
```

---

## 🔄 Alur Setup User

Setelah user berlangganan VIP, user cukup ketik `/setup` dan ikuti 3 langkah berikut:

```
1. Kirim nomor HP  →  +6281234567890
2. Kirim kode OTP  →  1 2 3 4 5
3. Kirim password 2FA (jika diaktifkan)
```

Session Telethon disimpan di database dan di-load otomatis setiap bot restart.

---

## 🗄️ Skema Database

| Tabel | Deskripsi |
|---|---|
| `users` | Data profil user (user_id, username, full_name) |
| `sessions` | String session Telethon per user |
| `subscriptions` | Data VIP (plan, paid_at, expired_at, is_active) |
| `user_settings` | Pengaturan per user (misal: auto_dl_view_once) |
| `blacklist_channels` | Daftar channel yang diblokir admin |
| `bc_group_blacklist` | Daftar grup yang diblokir per user untuk broadcast |

---

## 🧩 Cara Tambah Fitur Baru

### Command biasa (misal `/status`)
1. Buat `user/status.py` dengan fungsi `cmd_status(update, context)`
2. Di `main.py`: import fungsi → `app.add_handler(CommandHandler("status", cmd_status))`

### Fitur pakai Telethon client
1. Buat `user/fitur.py` dengan fungsi `register_fitur_handler(client, user_id)`
2. Di `auth/setup.py`: tambahkan `register_fitur_handler(client, user_id)` di dalam `register_telethon_handlers()`

### Fitur butuh data baru
1. Tambahkan fungsi di `database.py`
2. Tambahkan `CREATE TABLE IF NOT EXISTS ...` di `init_db()`

---

## 🛠️ Tech Stack

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v20+ — Bot API handler
- [Telethon](https://github.com/LonamiWebs/Telethon) — MTProto client (user session)
- [PostgreSQL](https://www.postgresql.org/) + [psycopg2](https://pypi.org/project/psycopg2/) — Database
- [Railway](https://railway.app) — Hosting & deployment

---

## 📄 Lisensi

Private — tidak untuk didistribusikan ulang tanpa izin.
