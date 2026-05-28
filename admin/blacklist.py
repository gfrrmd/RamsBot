from database import blacklist_add, blacklist_list, blacklist_remove


def build_blacklist_text() -> str:
    rows = blacklist_list()
    if not rows:
        return "🔒 *Blacklist Channel*\n\nDaftar kosong."
    lines = ["🔒 *Blacklist Channel*\n"]
    for i, r in enumerate(rows, 1):
        note = f" — {r['note']}" if r.get("note") else ""
        date = r.get("added_at", "")[:10]
        lines.append(f"{i}. `{r['identifier']}`{note} _(ditambah {date})_")
    return "\n".join(lines)
