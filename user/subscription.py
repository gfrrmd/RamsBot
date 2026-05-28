from datetime import datetime, timezone, timedelta

from database import get_subscription_info

WIB = timezone(timedelta(hours=7))


def _to_wib(dt: datetime) -> datetime:
    """Konversi datetime (naive/UTC) ke WIB."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB)


def build_subscription_text(uid: int) -> str:
    row = get_subscription_info(uid)
    if not row:
        return "❌ Kamu belum memiliki langganan VIP."
    paid_at, expired_at, is_active, plan = row
    try:
        exp = _to_wib(datetime.fromisoformat(expired_at))
        now = datetime.now(WIB)
        paid_dt = _to_wib(datetime.fromisoformat(paid_at)) if paid_at else None

        if plan == "trial":
            sisa_detik = max(int((exp - now).total_seconds()), 0)
            status = "✅ Aktif" if is_active and sisa_detik > 0 else "❌ Expired"
            menit = sisa_detik // 60
            detik = sisa_detik % 60
            paid_str = paid_dt.strftime("%d %b %Y, %H:%M WIB") if paid_dt else "—"
            exp_str = exp.strftime("%d %b %Y, %H:%M WIB")
            return (
                "🎟️ *Status Free Trial*\n\n"
                f"📅 Aktif sejak: {paid_str}\n"
                f"⏳ Berlaku hingga: {exp_str}\n"
                f"⏱️ Sisa: {menit} menit {detik} detik\n"
                f"Status: {status}\n\n"
                "Setelah trial habis, silakan upgrade ke VIP."
            )

        sisa = (exp.date() - now.date()).days
        status = "✅ Aktif" if is_active and sisa >= 0 else "❌ Expired"
        paid_str = paid_dt.strftime("%d %b %Y") if paid_dt else "—"
        exp_str = exp.strftime("%d %b %Y")
        return (
            "💎 *Status Langganan VIP*\n\n"
            f"📅 Aktif sejak: {paid_str}\n"
            f"⏳ Berlaku hingga: {exp_str}\n"
            f"🧩 Sisa: {max(sisa, 0)} hari\n"
            f"Status: {status}"
        )
    except Exception:
        return "⚠️ Data langganan tidak valid."
