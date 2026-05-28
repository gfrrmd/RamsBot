from datetime import datetime

from database import get_subscription_info


def build_subscription_text(uid: int) -> str:
    row = get_subscription_info(uid)
    if not row:
        return "❌ Kamu belum memiliki langganan VIP."
    paid_at, expired_at, is_active, plan = row
    try:
        exp = datetime.fromisoformat(expired_at)
        now = datetime.now()
        if plan == "trial":
            sisa_detik = max(int((exp - now).total_seconds()), 0)
            status = "✅ Aktif" if is_active and sisa_detik > 0 else "❌ Expired"
            menit = sisa_detik // 60
            detik = sisa_detik % 60
            return (
                "🎟️ *Status Free Trial*\n\n"
                f"📅 Aktif sejak: {paid_at[:19].replace('T', ' ') if paid_at else '—'}\n"
                f"⏳ Berlaku hingga: {expired_at[:19].replace('T', ' ')}\n"
                f"⏱️ Sisa: {menit} menit {detik} detik\n"
                f"Status: {status}\n\n"
                "Setelah trial habis, silakan upgrade ke VIP."
            )
        sisa = (exp - now).days
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
