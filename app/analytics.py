from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Users, Events


def get_db() -> Session:
    return SessionLocal()


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def get_activation_rate(
    db: Session,
    cohort_start: date,
    cohort_end: date,
) -> float:
    users = (
        db.query(Users)
        .filter(Users.signup_date >= cohort_start)
        .filter(Users.signup_date <= cohort_end)
        .all()
    )
    if not users:
        return 0.0

    user_ids = [u.user_id for u in users]
    events = (
        db.query(Events)
        .filter(Events.user_id.in_(user_ids))
        .filter(Events.event_name == "view_dashboard")
        .all()
    )

    events_by_user: Dict[str, List[Events]] = defaultdict(list)
    for e in events:
        events_by_user[e.user_id].append(e)

    activated = 0
    for u in users:
        signup_dt = datetime.combine(u.signup_date, datetime.min.time())
        cutoff = signup_dt + timedelta(days=7)
        has_activation = any(
            signup_dt <= e.event_time < cutoff for e in events_by_user[u.user_id]
        )
        if has_activation:
            activated += 1

    return activated / len(users)


def get_wau_by_plan(
    db: Session,
    start_date: date,
    end_date: date,
) -> List[Dict]:
    events = (
        db.query(Events)
        .filter(Events.event_time >= datetime.combine(start_date, datetime.min.time()))
        .filter(Events.event_time < datetime.combine(end_date, datetime.min.time()))
        .all()
    )

    user_ids = list({e.user_id for e in events})
    users = (
        db.query(Users)
        .filter(Users.user_id.in_(user_ids))
        .all()
    )
    plan_by_user = {u.user_id: u.plan_tier for u in users}

    buckets: Dict[Tuple[date, str], set] = defaultdict(set)

    for e in events:
        d = e.event_time.date()
        w_start = _week_start(d)
        plan = plan_by_user.get(e.user_id)
        if plan is None:
            continue
        buckets[(w_start, plan)].add(e.user_id)

    result = []
    for (w_start, plan), users_set in sorted(buckets.items(), key=lambda x: (x[0][0], x[0][1])):
        result.append(
            {
                "week_start": w_start.isoformat(),
                "plan_tier": plan,
                "wau": len(users_set),
            }
        )
    return result


def get_feature_timeseries(
    db: Session,
    event_name: str,
    start_date: date,
    end_date: date,
) -> List[Dict]:
    events = (
        db.query(Events)
        .filter(Events.event_name == event_name)
        .filter(Events.event_time >= datetime.combine(start_date, datetime.min.time()))
        .filter(Events.event_time < datetime.combine(end_date, datetime.min.time()))
        .all()
    )

    counts: Dict[date, int] = defaultdict(int)
    for e in events:
        d = e.event_time.date()
        counts[d] += 1

    result = []
    for d, c in sorted(counts.items(), key=lambda x: x[0]):
        result.append(
            {
                "date": d.isoformat(),
                "event_name": event_name,
                "count": c,
            }
        )
    return result


def get_conversion_by_channel(
    db: Session,
    cohort_start: date,
    cohort_end: date,
) -> List[Dict]:
    users = (
        db.query(Users)
        .filter(Users.signup_date >= cohort_start)
        .filter(Users.signup_date <= cohort_end)
        .all()
    )
    if not users:
        return []

    user_ids = [u.user_id for u in users]
    signup_by_user = {u.user_id: u.signup_date for u in users}
    channel_by_user = {u.user_id: u.acquisition_channel for u in users}

    events = (
        db.query(Events)
        .filter(Events.user_id.in_(user_ids))
        .filter(Events.event_name == "upgrade_plan")
        .all()
    )

    converted_users_by_channel: Dict[str, set] = defaultdict(set)

    for e in events:
        uid = e.user_id
        signup_date = signup_by_user.get(uid)
        if signup_date is None:
            continue
        start_dt = datetime.combine(signup_date, datetime.min.time())
        cutoff = start_dt + timedelta(days=30)
        if start_dt <= e.event_time < cutoff:
            ch = channel_by_user.get(uid)
            if ch is not None:
                converted_users_by_channel[ch].add(uid)

    cohort_by_channel: Dict[str, set] = defaultdict(set)
    for u in users:
        cohort_by_channel[u.acquisition_channel].add(u.user_id)

    result = []
    for ch, cohort_users in cohort_by_channel.items():
        converted = converted_users_by_channel.get(ch, set())
        total = len(cohort_users)
        if total == 0:
            rate = 0.0
        else:
            rate = len(converted) / total
        result.append(
            {
                "acquisition_channel": ch,
                "cohort_size": total,
                "converted": len(converted),
                "conversion_rate_30d": rate,
            }
        )
    return sorted(result, key=lambda x: x["acquisition_channel"])


def get_feature_usage_by_segment(
    db: Session,
    plan_tier: str,
    start_date: date,
    end_date: date,
) -> List[Dict]:
    users = (
        db.query(Users)
        .filter(Users.plan_tier == plan_tier)
        .all()
    )
    if not users:
        return []

    user_ids = [u.user_id for u in users]

    events = (
        db.query(Events)
        .filter(Events.user_id.in_(user_ids))
        .filter(Events.event_time >= datetime.combine(start_date, datetime.min.time()))
        .filter(Events.event_time < datetime.combine(end_date, datetime.min.time()))
        .all()
    )

    counts: Dict[str, int] = defaultdict(int)
    users_by_event: Dict[str, set] = defaultdict(set)

    for e in events:
        counts[e.event_name] += 1
        users_by_event[e.event_name].add(e.user_id)

    result = []
    for event_name, total_count in counts.items():
        result.append(
            {
                "event_name": event_name,
                "total_events": total_count,
                "distinct_users": len(users_by_event[event_name]),
            }
        )

    result.sort(key=lambda x: x["distinct_users"], reverse=True)
    return result


def get_country_wow_change(
    db: Session,
    week0_start: date,
    week1_start: date,
    drop_threshold: float = 0.2,
) -> List[Dict]:
    week0_end = week0_start + timedelta(days=7)
    week1_end = week1_start + timedelta(days=7)

    events = (
        db.query(Events)
        .filter(Events.event_time >= datetime.combine(week0_start, datetime.min.time()))
        .filter(Events.event_time < datetime.combine(week1_end, datetime.min.time()))
        .all()
    )

    user_ids = list({e.user_id for e in events})
    users = (
        db.query(Users)
        .filter(Users.user_id.in_(user_ids))
        .all()
    )
    country_by_user = {u.user_id: u.country for u in users}

    wau_week0: Dict[str, set] = defaultdict(set)
    wau_week1: Dict[str, set] = defaultdict(set)

    for e in events:
        d = e.event_time.date()
        country = country_by_user.get(e.user_id)
        if country is None:
            continue
        if week0_start <= d < week0_end:
            wau_week0[country].add(e.user_id)
        elif week1_start <= d < week1_end:
            wau_week1[country].add(e.user_id)

    result = []
    countries = set(list(wau_week0.keys()) + list(wau_week1.keys()))

    for c in countries:
        w0 = len(wau_week0.get(c, set()))
        w1 = len(wau_week1.get(c, set()))
        if w0 == 0:
            change_pct = None
        else:
            change_pct = (w1 - w0) / w0
        if change_pct is not None and change_pct <= -drop_threshold:
            result.append(
                {
                    "country": c,
                    "wau_week0": w0,
                    "wau_week1": w1,
                    "change_pct": change_pct,
                }
            )

    result.sort(key=lambda x: x["change_pct"])
    return result


if __name__ == "__main__":
    db = get_db()
    today = date.today()
    cohort_start = today - timedelta(days=14)
    cohort_end = today - timedelta(days=7)

    ar = get_activation_rate(db, cohort_start, cohort_end)
    print("activation_rate_7d", ar)

    wau = get_wau_by_plan(db, today - timedelta(days=28), today)
    print("wau_by_plan", wau[:5])

    ts = get_feature_timeseries(db, "export_report", today - timedelta(days=30), today)
    print("feature_timeseries sample", ts[:5])

    conv = get_conversion_by_channel(db, cohort_start, cohort_end)
    print("conversion_by_channel", conv)

    fu = get_feature_usage_by_segment(db, "enterprise", today - timedelta(days=30), today)
    print("feature_usage_by_segment sample", fu)

    w0 = _week_start(today - timedelta(days=14))
    w1 = w0 + timedelta(days=7)
    wow = get_country_wow_change(db, w0, w1)
    print("country_wow_change", wow)
    db.close()