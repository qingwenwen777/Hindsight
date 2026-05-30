"""日报生成任务状态模型。

记录一次日报生成的可查询状态：阶段、进度、结果文档、错误。
前端通过轮询任务状态实现"可感知的异步生成"。
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


# 任务状态
JOB_PENDING = "PENDING"      # 已入队，尚未开始
JOB_RUNNING = "RUNNING"      # 执行中
JOB_SUCCESS = "SUCCESS"      # 成功
JOB_FAILED = "FAILED"        # 失败

# 阶段（用于前端展示"在生成什么"）
STAGE_QUEUED = "QUEUED"            # 排队中
STAGE_CONTEXT = "CONTEXT"          # 收集行情/异动/待办
STAGE_AI = "AI"                    # AI 叙述生成中
STAGE_SAVING = "SAVING"            # 写入文档
STAGE_DONE = "DONE"                # 完成


class ReportJob(SQLModel, table=True):
    """日报生成任务。

    一次手动/定时生成对应一条记录，状态机：
      PENDING → RUNNING(stage=CONTEXT→AI→SAVING) → SUCCESS/FAILED
    """

    __tablename__ = "report_jobs"

    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True)  # US/CN/HK/JP
    status: str = Field(default=JOB_PENDING, index=True)
    stage: str = Field(default=STAGE_QUEUED)
    progress: int = Field(default=0)  # 0-100
    message: str | None = None  # 阶段说明 / 失败原因
    document_id: int | None = Field(default=None, foreign_key="insight_documents.id")
    degraded: bool = False
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None


__all__ = [
    "ReportJob",
    "JOB_PENDING",
    "JOB_RUNNING",
    "JOB_SUCCESS",
    "JOB_FAILED",
    "STAGE_QUEUED",
    "STAGE_CONTEXT",
    "STAGE_AI",
    "STAGE_SAVING",
    "STAGE_DONE",
]
