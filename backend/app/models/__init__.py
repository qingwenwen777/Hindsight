"""SQLModel 数据模型包。

集中导入所有模型，确保 SQLModel.metadata 注册全部表（供 Alembic 与建表使用）。
"""

from app.models.ai_insight import AiInsight
from app.models.ai_provider import AiProvider
from app.models.cash import CashAccount, CashFlow
from app.models.conversation import Conversation, ConversationMessage
from app.models.corporate_action import CorporateAction
from app.models.fee_rule import FeeRule
from app.models.financials import Financial
from app.models.fx_rate import FxRate
from app.models.insight import InsightDocument, PriceAlert, ReportConfig, ScreenerRule
from app.models.journal import Journal, Review
from app.models.report_job import ReportJob
from app.models.stock import Price, Stock
from app.models.sync_log import SyncLog
from app.models.sync_setting import SyncSetting
from app.models.transaction import Transaction
from app.models.watchlist import Watchlist

__all__ = [
    "Stock",
    "Price",
    "Transaction",
    "CorporateAction",
    "Journal",
    "Review",
    "FeeRule",
    "SyncLog",
    "SyncSetting",
    "FxRate",
    "CashAccount",
    "CashFlow",
    "AiInsight",
    "Watchlist",
    "Financial",
    "InsightDocument",
    "ReportConfig",
    "ScreenerRule",
    "PriceAlert",
    "ReportJob",
    "Conversation",
    "ConversationMessage",
    "AiProvider",
]
