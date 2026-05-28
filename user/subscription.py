from datetime import datetime

from database import get_subscription_info


def build_subscription_text(uid: int) -> str:
    row = get_subscription_info(uid)
    if not row:
        return "❌ Kamu belum memiliki langganan VIP."
    paid_at, expired_at, is_active = row
    try:
        exp = datetime.fromisoformat(expired_at)
        sisa = (exp - datetime.now()).days
        status = "✅ Aktif" if is_active and sisa >= 0 else "❌ Expired"
        return (
            "💎 *Status Langganan VIP*\n\n"
            f"📅 Aktif sejak: {paid_at[:10] if paid_at else '—'}\n"
            f"⏳ Berlaku hingga: {expired_at[:10]}\n"
            f"🧉 Sisa: {max(sisa, 0)} hari\n"
            f"Status: {status}"
        )
    except Exception:
        return "⚠️ Data langganan tidak valid."
