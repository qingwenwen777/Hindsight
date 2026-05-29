"""日志锁定守卫（设计文档 5.3 / F7.1）。

提交后的 journal（is_locked=True）不可被 UPDATE，只能追加 review。
用 SQLAlchemy 的 before_flush 事件在 ORM 层拦截对已锁定 journal 本体的修改。

允许的例外：
- 把 is_locked 从 False 改为 True（即"提交锁定"动作本身）。
- locked_at 在锁定时一并写入。
"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.orm import Session as SaSession
from sqlalchemy.orm.attributes import get_history

from app.models.journal import Journal


class JournalLockedError(Exception):
    """试图修改已锁定的决策日志。"""


# 锁定后仍允许变化的字段（解锁动作本身需要的字段）
_ALLOWED_ON_LOCKED: set[str] = set()


def _is_unlock_or_lock_transition(obj: Journal) -> bool:
    """判断本次修改是否是"加锁动作"（is_locked False→True）。"""
    hist = get_history(obj, "is_locked")
    # hist.deleted 是旧值列表
    if hist.deleted and hist.deleted[0] is False and obj.is_locked is True:
        return True
    return False


def install_journal_lock_guard() -> None:
    """注册全局 before_flush 监听，拦截对已锁定 journal 的修改。"""

    from sqlalchemy import event

    @event.listens_for(SaSession, "before_flush")
    def _before_flush(session: SaSession, flush_context, instances) -> None:  # noqa: ANN001, ARG001
        for obj in session.dirty:
            if not isinstance(obj, Journal):
                continue
            if not session.is_modified(obj, include_collections=False):
                continue

            state = inspect(obj)
            # 取出本次被修改的字段名
            changed = {
                attr.key
                for attr in state.attrs
                if get_history(obj, attr.key).has_changes()
            }
            if not changed:
                continue

            # 加锁动作本身放行
            if _is_unlock_or_lock_transition(obj):
                # 仅允许同时变更 is_locked / locked_at
                if changed - {"is_locked", "locked_at"}:
                    raise JournalLockedError(
                        f"锁定 journal#{obj.id} 时不得同时修改其它字段：{changed}"
                    )
                continue

            # 已锁定状态下的任何修改都拒绝
            # 取数据库中的原 is_locked 值（旧值），若旧值已是 True 则拦截
            locked_hist = get_history(obj, "is_locked")
            was_locked = (
                locked_hist.deleted[0]
                if locked_hist.deleted
                else obj.is_locked
            )
            if was_locked and (changed - _ALLOWED_ON_LOCKED):
                raise JournalLockedError(
                    f"journal#{obj.id} 已锁定，不可修改字段：{changed}（仅可追加 review）"
                )
