# Python Entity Framework
Persistence for attr-based Python classes.

# Example
```python
from entity_framework import Entity, Identity, Repository
from entity_framework.storages.sqlalchemy import SqlAlchemyRepo


# Write your business entities in almost-plain Python
class Customer(Entity):
    id: Identity[int]
    full_name: str


# Get abstract base class for repo
CustomerRepo = Repository[Customer, int]  # first argument - entity class, second - Identity field type


# Setup your persistence as usual
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Setup registry and get concrete class
from entity_framework.storages.sqlalchemy import SqlAlchemyRepo
from entity_framework.storages.sqlalchemy.registry import SaRegistry


Registry = SaRegistry()


class SaCustomerRepo(SqlAlchemyRepo, CustomerRepo):
    base = Base
    registry = Registry
```
Voilà. Python Entity Framework will generate SQLAlchemy's model for you. *They are properly detected by alembic (yay!)* Additionally, `SaCustomerRepo` will have two methods - save & get to respectively persist and fetch your entity.

# WORK IN PROGRESS
Everything is subjected to change, including name of the library and address of this repository. Code inside may be inconsistent and is undergoing significant refactorings all the time.

## Aim
To get rid of necessity of manual writing code for persisting attr-based business entities AKA aggregates. 


## Roadmap
* Support SQLAlchemy with possibilities of overriding implementation partially (e.g. single column definitions) or entirely
* Use SQLAlchemy's Session as UnitOfWork
* Optimize code for populating models/entities
* Support MongoDB with the same set of functionalities as SQLAlchemy storage
