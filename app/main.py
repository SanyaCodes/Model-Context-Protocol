from datetime import datetime, date, timedelta
from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from .db import SessionLocal
from . import analytics
from .schemas import (
    ActivationRateResponse,
    WAUByPlanResponse,
    FeatureTimeseriesResponse,
    ConversionByChannelResponse,
    FeatureUsageBySegmentResponse,
    CountryWoWChangeResponse,
)


app = FastAPI(title="Feature Analytics Service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics/activation_rate", response_model=ActivationRateResponse)
def activation_rate(
    cohort_start: str,
    cohort_end: str,
    db: Session = Depends(get_db),
):
    cs = date.fromisoformat(cohort_start)
    ce = date.fromisoformat(cohort_end)
    rate = analytics.get_activation_rate(db, cs, ce)
    return {"activation_rate_7d": rate}


@app.get("/metrics/wau_by_plan", response_model=WAUByPlanResponse)
def wau_by_plan(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
):
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    items = analytics.get_wau_by_plan(db, sd, ed)
    return {"items": items}


@app.get("/metrics/feature_timeseries", response_model=FeatureTimeseriesResponse)
def feature_timeseries(
    event_name: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
):
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    items = analytics.get_feature_timeseries(db, event_name, sd, ed)
    return {"items": items}


@app.get("/metrics/conversion_by_channel", response_model=ConversionByChannelResponse)
def conversion_by_channel(
    cohort_start: str,
    cohort_end: str,
    db: Session = Depends(get_db),
):
    cs = date.fromisoformat(cohort_start)
    ce = date.fromisoformat(cohort_end)
    items = analytics.get_conversion_by_channel(db, cs, ce)
    return {"items": items}


@app.get("/metrics/feature_usage_by_segment", response_model=FeatureUsageBySegmentResponse)
def feature_usage_by_segment(
    plan_tier: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
):
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    items = analytics.get_feature_usage_by_segment(db, plan_tier, sd, ed)
    return {"items": items}


@app.get("/metrics/country_wow_change", response_model=CountryWoWChangeResponse)
def country_wow_change(
    week0_start: str,
    week1_start: str,
    drop_threshold: float = 0.2,
    db: Session = Depends(get_db),
):
    w0 = date.fromisoformat(week0_start)
    w1 = date.fromisoformat(week1_start)
    items = analytics.get_country_wow_change(db, w0, w1, drop_threshold=drop_threshold)
    return {"items": items}