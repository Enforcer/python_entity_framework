import typing
import uuid

from entity_framework import Entity, Identity, ValueObject, Repository
from entity_framework.storages.sqlalchemy import SqlAlchemyRepo
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LastTx(ValueObject):
    guid: uuid.UUID


class Wallet(ValueObject):
    balance: int
    currency: str
    last_tx: typing.Optional[LastTx]


class YouNameIt(Entity):
    id: Identity[int]
    favourite_wallet: typing.Optional[Wallet]
    wallets: typing.List[Wallet]


YouNameItRepo = Repository[YouNameIt, int]  # this one's abstract


class ConreteYouNameItRepo(SqlAlchemyRepo, YouNameItRepo):
    base = Base


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine('postgresql://postgres:dbpasswd@localhost:5432/plays', echo=True)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(engine)

repo = ConreteYouNameItRepo(session=Session())
entity = YouNameIt(id=1, favourite_wallet=Wallet(10, 'PLN', LastTx(uuid.uuid4())), wallets=[])
repo.save(entity)
reloaded = repo.get(entity.id)
assert reloaded == entity, f'\n{reloaded}\n{entity}'
