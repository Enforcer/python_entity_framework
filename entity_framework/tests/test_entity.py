import typing

import pytest

from entity_framework.entity import (
    Entity,
    EntityWithoutIdentity,
    Identity,
    ValueObject,
    ValueObjectWithIdentity,
    EntityNestedInValueObject,
)


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
    class WithDoubleIdentity(Entity):
        id: Identity[int]
        second_id: Identity[int]

    entity = WithDoubleIdentity(1, 2)
    assert entity.id == 1
    assert entity.second_id == 2


def test_value_object_without_identity():
    class SomeValueObject(ValueObject):
        amount: int

    assert SomeValueObject(1).amount == 1


def test_value_object_with_identity():
    with pytest.raises(ValueObjectWithIdentity):

        class IllegalValueObject(ValueObject):
            id: Identity[int]

        IllegalValueObject(1)


def test_vo_can_be_nested_inside_another_vo():
    class A(ValueObject):
        name: str

    class B(ValueObject):
        age: int
        nested: A

    assert B(1, A("John"))


def test_entity_can_not_be_nested_inside_vo():
    class Human(Entity):
        id: Identity[int]
        name: str

    with pytest.raises(Exception):

        class A(ValueObject):
            score: int
            person: Human


def test_nullable_entity_can_not_be_nested_inside_vo():
    class Person(Entity):
        id: Identity[int]
        name: str

    with pytest.raises(Exception):

        class B(ValueObject):
            score: int
            person: typing.Optional[Person]
