"""暴露与集中度 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.money import quantize_money, to_db_str
from app.core.response import ok
from app.database import get_session
from app.services.biases.concentration import ExposureSlice, compute_concentration

router = APIRouter(prefix="/portfolio", tags=["exposure"])


def _slice(s: ExposureSlice) -> dict:
    return {
        "key": s.key,
        "name": s.name,
        "value": to_db_str(quantize_money(s.value)),
        "weight": float(round(s.weight, 6)),
        "weight_pct": float(round(s.weight * 100, 2)),
        "over_threshold": s.over_threshold,
    }


@router.get("/exposure", summary="暴露分析")
def get_exposure(
    dimension: str = Query("industry", description="industry | market | currency"),
    currency: str = Query("JPY"),
    session: Session = Depends(get_session),
) -> dict:
    """按维度返回暴露切片。"""
    report = compute_concentration(session, currency)
    dim = dimension.lower()
    mapping = {
        "industry": report.by_industry,
        "market": report.by_market,
        "currency": report.by_currency,
        "stock": report.by_stock,
    }
    slices = mapping.get(dim, report.by_industry)
    return ok(
        {
            "dimension": dim,
            "currency": report.currency,
            "total_value": to_db_str(quantize_money(report.total_value)),
            "slices": [_slice(s) for s in slices],
        }
    )


@router.get("/concentration", summary="集中度（含告警）")
def get_concentration(
    currency: str = Query("JPY"),
    session: Session = Depends(get_session),
) -> dict:
    """集中度全维度 + 超阈值告警。"""
    report = compute_concentration(session, currency)
    return ok(
        {
            "currency": report.currency,
            "total_value": to_db_str(quantize_money(report.total_value)),
            "by_stock": [_slice(s) for s in report.by_stock],
            "by_industry": [_slice(s) for s in report.by_industry],
            "by_market": [_slice(s) for s in report.by_market],
            "by_currency": [_slice(s) for s in report.by_currency],
            "alerts": report.alerts,
        }
    )
