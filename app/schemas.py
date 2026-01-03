from typing import List, Optional
from pydantic import BaseModel


class ActivationRateResponse(BaseModel):
    activation_rate_7d: float


class WAUByPlanItem(BaseModel):
    week_start: str
    plan_tier: str
    wau: int


class FeatureTimeseriesItem(BaseModel):
    date: str
    event_name: str
    count: int


class ConversionByChannelItem(BaseModel):
    acquisition_channel: str
    cohort_size: int
    converted: int
    conversion_rate_30d: float


class FeatureUsageBySegmentItem(BaseModel):
    event_name: str
    total_events: int
    distinct_users: int


class CountryWoWChangeItem(BaseModel):
    country: str
    wau_week0: int
    wau_week1: int
    change_pct: float


# wrappers for list responses

class WAUByPlanResponse(BaseModel):
    items: List[WAUByPlanItem]


class FeatureTimeseriesResponse(BaseModel):
    items: List[FeatureTimeseriesItem]


class ConversionByChannelResponse(BaseModel):
    items: List[ConversionByChannelItem]


class FeatureUsageBySegmentResponse(BaseModel):
    items: List[FeatureUsageBySegmentItem]


class CountryWoWChangeResponse(BaseModel):
    items: List[CountryWoWChangeItem]