PHONE_STEP, CODE_STEP, PASSWORD_STEP = range(3)

temp_store: dict[int, dict] = {}
waiting_restore: set[int] = set()
waiting_gift: set[int] = set()
waiting_revoke: set[int] = set()


def clear_user_state(uid: int):
    temp_store.pop(uid, None)
    waiting_restore.discard(uid)
    waiting_gift.discard(uid)
    waiting_revoke.discard(uid)
    try:
        from admin.callbacks import waiting_bl_add, waiting_bl_remove
        waiting_bl_add.discard(uid)
        waiting_bl_remove.discard(uid)
    except Exception:
        pass
