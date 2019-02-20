# TODO: add __all__
from entity_framework.entity import Entity, Identity, ValueObject
from entity_framework.repository import Repository


# TODO: what to do with SQLAlchemy's UoW? Wrap it, trick it (ouch), ignore it?
# Maybe one could alter entities to become PROXY OBJECTS for models, so that one
# does not have to update all fields at once neither use merge with load=True
# PoC done: data is copied to entity inside identity map, but one has to keep around another reference to the entity
# or Garbage Collector deletes it.

# TODO: support custom Value Objects, map them onto columns in DB back and forth. Single-dispatch?

# TODO: Value objects will still have to have IDs in underlying DB, does not matter if it is PostgreSQL or MongoDB
