import enum
import typing
import uuid
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from entity_framework import Entity, Identity, create_declarative_repo_base, create_repo


PlanId = uuid.UUID
SubscriberId = uuid.UUID


class Plan(Entity):
    id: Identity[PlanId]
    discount: float


class Subscription(Entity):
    plan_id: PlanId
    start: date
    end: date
    tier: int
    cancelled_at: typing.Optional[date] = None


class LifetimeSubscription(Entity):
    plan_id: PlanId
    start: date
    tier: int
    cancelled_at: typing.Optional[date] = None


class Status(enum.Enum):
    NEW = "NEW"
    OLD = "OLD"


class Subscriber(Entity):
    id: Identity[SubscriberId]
    name: str
    status: Status
    current_subscription_cancelled_at: date
    subscription: typing.Optional[Subscription] = None
    lifetime_subscription: typing.Optional[LifetimeSubscription] = None

    past_subscriptions: typing.List[PastSubscription]

    def subscribe(self, plan_id: PlanId, plan_tier: int) -> None:
        if not self.subscription:
            self.subscription = Subscription(plan_id, date.today(), date.today() + timedelta(days=30), plan_tier)

    def cancel(self) -> None:
        if self.subscription:
            self.subscription.cancelled_at = date.today()


subscriber_id = uuid.uuid4()
plan_id = uuid.uuid4()
subscriber = Subscriber(subscriber_id, "Seba", Status.NEW)
subscriber.subscribe(plan_id=plan_id, plan_tier=1)


Base = declarative_base()
Repo = create_declarative_repo_base(Base)


# class SubscriberRepo(Repo[Subscriber, uuid.UUID]):
#     pass


SubscriberRepo = create_repo(Base, Subscriber, uuid.UUID)

engine = create_engine("postgresql://postgres:dbpasswd@localhost:5432/plays", echo=True)
Base.metadata.create_all(engine)
SessionC = sessionmaker(bind=engine)

repo = SubscriberRepo(SessionC())

repo.save(subscriber)

got_subscriber = repo.get(subscriber_id)

assert got_subscriber == subscriber, f"\n{got_subscriber}\n{subscriber}"


subscriber.cancel()
repo.save(subscriber)

import atexit


@atexit.register
def finalize():
    SessionC.close_all()
    Base.metadata.drop_all(engine)
