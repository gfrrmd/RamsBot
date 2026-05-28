import time
from datetime import datetime, timezone, timedelta

from client_manager import active_clients, _start_time
from database import get_subscription_info

WIB = timezone(timedelta(hours=7))


def _to_wib(dt: datetime) -> datetime:
    """Konversi datetime (naive/UTC) ke WIB."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB)


def _format_uptime(uid: int) -> str:
    start = _start_time.get(uid)
    if start is None:
        return "—"
    elapsed = int(time.monotonic() - start)
    jam = elapsed // 3600
    menit = (elapsed % 3600) // 60
    detik = elapsed % 60
    return f"{jam:02d}:{menit:02d}:{detik:02d}"


def build_subscription_text(uid: int, full_name: str = None, username: str = None) -> str:
    row = get_subscription_info(uid)

    # Info user
    name_str = full_name or "—"
    username_str = f"@{username}" if username else "—"

    # Status bot (session aktif atau tidak)
    client = active_clients.get(uid)
    bot_active = client and client.is_connected()
    status_bot = "Aktif ✅" if bot_active else "Tidak Aktif ❌"

    # Uptime
    uptime_str = _format_uptime(uid)

    if not row:
        return (
            "*👤 Status Akun*\n\n"
            f"Pengguna: {name_str}\n"
            f"Username: {username_str}\n"
            f"ID: `{uid}`\n"
            f"Status Bot: {status_bot}\n"
            "Plan: —\n"
            "Expired: —\n"
            f"Uptime Bot: {uptime_str}"
        )

    paid_at, expired_at, is_active, plan = row
    try:
        exp = _to_wib(datetime.fromisoformat(expired_at))
        now = datetime.now(WIB)

        if plan == "trial":
            sisa_detik = max(int((exp - now).total_seconds()), 0)
            sub_active = is_active and sisa_detik > 0
            plan_str = "Trial"
            exp_str = exp.strftime("%d %b %Y, %H:%M WIB")
        else:
            sisa = (exp.date() - now.date()).days
            sub_active = is_active and sisa >= 0
            plan_str = "VIP 💎"
            exp_str = exp.strftime("%d %b %Y")

        status_bot_final = "Aktif ✅" if bot_active else "Tidak Aktif ❌"

        return (
            "*👤 Status Akun*\n\n"
            f"Pengguna: {name_str}\n"
            f"Username: {username_str}\n"
            f"ID: `{uid}`\n"
            f"Status Bot: {status_bot_final}\n"
            f"Plan: {plan_str}\n"
            f"Expired: {exp_str}\n"
            f"Uptime Bot: {uptime_str}"
        )
    except Exception:
        return "⚠️ Data langganan tidak valid."
