import uuid
import random
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Users, Companies, Events


COUNTRIES = ["US", "UK", "DE", "IN", "CA"]
PLANS = ["free", "pro", "enterprise"]
CHANNELS = ["organic", "paid", "referral"]
EVENTS = [
    "signup",
    "login",
    "view_dashboard",
    "export_report",
    "invite_teammate",
    "upgrade_plan",
]


def random_date(start_date: date, end_date: date):
    delta = (end_date - start_date).days
    return start_date + timedelta(days=random.randint(0, delta))


def main():
    db: Session = SessionLocal()

    random.seed(42)

    companies = []
    for _ in range(50):
        cid = str(uuid.uuid4())
        company = Companies(
            company_id=cid,
            company_name=f"Company_{cid[:8]}",
            employee_count=random.randint(3, 500),
        )
        companies.append(company)
        db.add(company)

    db.commit()

    users = []
    start = date.today() - timedelta(days=120)
    end = date.today()

    for _ in range(2000):
        uid = str(uuid.uuid4())
        company = random.choice(companies)
        signup = random_date(start, end)
        plan = random.choices(
            PLANS,
            weights=[0.6, 0.3, 0.1],
            k=1,
        )[0]

        user = Users(
            user_id=uid,
            company_id=company.company_id,
            country=random.choice(COUNTRIES),
            plan_tier=plan,
            signup_date=signup,
            acquisition_channel=random.choice(CHANNELS),
        )
        users.append(user)
        db.add(user)

    db.commit()

    events = []

    for u in users:
        # signup event
        events.append(
            Events(
                event_id=str(uuid.uuid4()),
                user_id=u.user_id,
                event_name="signup",
                event_time=datetime.combine(u.signup_date, datetime.min.time())
                + timedelta(hours=random.randint(0, 23)),
                event_metadata={},
            )
        )

        # simulate activity days
        days_active = random.randint(0, 40)

        for d in range(days_active):
            day = u.signup_date + timedelta(days=d)
            if day > date.today():
                break

            daily_events = random.randint(0, 4)

            for _ in range(daily_events):
                name = random.choices(
                    EVENTS[1:],  # exclude signup
                    weights=[0.4, 0.3, 0.15, 0.1, 0.05],
                    k=1,
                )[0]

                events.append(
                    Events(
                        event_id=str(uuid.uuid4()),
                        user_id=u.user_id,
                        event_name=name,
                        event_time=datetime.combine(day, datetime.min.time())
                        + timedelta(hours=random.randint(8, 22)),
                        event_metadata={},
                    )
                )

    db.bulk_save_objects(events)
    db.commit()

    db.close()


if __name__ == "__main__":
    main()