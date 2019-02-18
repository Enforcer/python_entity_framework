import pytest

from entity_framework.entity import Entity, EntityWithoutIdentity, Identity, ValueObject, ValueObjectWithIdentity


def test_entity_allows_one_with_identity():
    class WithIdentity(Entity):
        id: Identity[int]

    assert WithIdentity(1).id == 1


def test_entity_enforces_identity():
    with pytest.raises(EntityWithoutIdentity):

        class Identless(Entity):
            name: str

        Identless("Some name")


def test_entity_allows_multiple_identities():
    raise pytest.skip("Not implemented yet!")


def test_value_object_without_identity():
    class SomeValueObject(ValueObject):
        amount: int

    assert SomeValueObject(1).amount == 1


def test_value_object_with_identity():
    with pytest.raises(ValueObjectWithIdentity):

        class IllegalValueObject(ValueObject):
            id: Identity[int]

        IllegalValueObject(1)
