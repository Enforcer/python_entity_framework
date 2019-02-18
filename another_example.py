from typing import Optional

from entity_framework import Entity, ValueObject, Identity, Repository
from entity_framework.storages.sqlalchemy import SqlAlchemyRepo

from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


SubscriberId = int
PlanId = int


class Plan(Entity):
    id: Identity[PlanId]
    discount: float


class Subscription(ValueObject):
    plan_id: PlanId
    start_at: int


class Subscriber(Entity):
    id: Identity[SubscriberId]
    current_subscription: Optional[Subscription]
    lifetime_subscription: Optional[Subscription]

    def subscribe(self, subscription: Subscription) -> None:
        if not self.current_subscription:
            self.current_subscription = subscription
        else:
            raise Exception('nu nu')


SubscriberRepo = Repository[Subscriber, SubscriberId]


class SqlSubscriberRepo(SqlAlchemyRepo, SubscriberRepo):
    base = Base


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine('postgresql://postgres:dbpasswd@localhost:5432/plays', echo=True)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(engine)

repo = SqlSubscriberRepo(Session())
repo.save(Subscriber(1, None, None))
