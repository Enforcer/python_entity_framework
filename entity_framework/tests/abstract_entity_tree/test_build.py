import typing
from decimal import Decimal
from enum import Enum
from uuid import UUID

from entity_framework import abstract_entity_tree
from entity_framework.abstract_entity_tree import (
    AbstractEntityTree,
    EntityNode,
    FieldNode,
    ValueObjectNode,
    ListOfValueObjectsNode,
)
from entity_framework import Entity, Identity, ValueObject


class DummyEnum(Enum):
    FIRST_VALUE = "FIRST_VALUE"
    ANOTHER_VALUE = "ANOTHER_VALUE"


class SimpleFlat(Entity):
    guid: Identity[UUID]
    name: typing.Optional[str]
    score: int
    enumerated: DummyEnum
    balance: typing.Optional[Decimal]


def test_builds_simple_flat_entity():
    result = abstract_entity_tree.build(SimpleFlat)

    assert result == AbstractEntityTree(
        root=EntityNode(
            name="simple_flat",
            type=SimpleFlat,
            nullable=False,
            children=(
                FieldNode(name="guid", type=UUID, nullable=False, children=(), is_identity=True),
                FieldNode(name="name", type=str, nullable=True, children=(), is_identity=False),
                FieldNode(name="score", type=int, nullable=False, children=(), is_identity=False),
                FieldNode(name="enumerated", type=DummyEnum, nullable=False, children=(), is_identity=False),
                FieldNode(name="balance", type=Decimal, nullable=True, children=(), is_identity=False),
            ),
        )
    )


class NestedValueObject(ValueObject):
    amount: Decimal
    currency: str


class NestedEntity(Entity):
    nested_guid: Identity[UUID]
    name: typing.Optional[str]


class SomeAggregate(Entity):
    guid: Identity[UUID]
    nested: NestedEntity
    balance: NestedValueObject


def test_builds_aggregate_with_embedded_entity_and_value_object():
    result = abstract_entity_tree.build(SomeAggregate)

    assert result == AbstractEntityTree(
        root=EntityNode(
            name="some_aggregate",
            type=SomeAggregate,
            nullable=False,
            children=(
                FieldNode(name="guid", type=UUID, nullable=False, children=(), is_identity=True),
                EntityNode(
                    name="nested",
                    type=NestedEntity,
                    children=(
                        FieldNode(name="nested_guid", type=UUID, nullable=False, children=(), is_identity=True),
                        FieldNode(name="name", type=str, nullable=True, children=(), is_identity=False),
                    ),
                ),
                ValueObjectNode(
                    name="balance",
                    type=NestedValueObject,
                    nullable=False,
                    children=(
                        FieldNode(name="amount", type=Decimal, nullable=False, children=(), is_identity=False),
                        FieldNode(name="currency", type=str, nullable=False, children=(), is_identity=False),
                    ),
                ),
            ),
        )
    )


class AggregateWithValueObjectList(Entity):
    id: Identity[int]
    wallets: typing.List[NestedValueObject]


def test_builds_aggregate_with_list_of_value_objects():
    result = abstract_entity_tree.build(AggregateWithValueObjectList)

    assert result == AbstractEntityTree(
        root=EntityNode(
            name="aggregate_with_value_object_list",
            type=AggregateWithValueObjectList,
            nullable=False,
            children=(
                FieldNode(name="id", type=int, nullable=False, children=(), is_identity=True),
                ListOfValueObjectsNode(
                    name="wallets",
                    type=NestedValueObject,
                    nullable=False,
                    children=(
                        FieldNode(name="amount", type=Decimal, nullable=False, children=(), is_identity=False),
                        FieldNode(name="currency", type=str, nullable=False, children=(), is_identity=False),
                    ),
                ),
            ),
        )
    )


class AggregateWithOptionalNested(Entity):
    id: Identity[int]
    wallet: typing.Optional[NestedValueObject]


def test_optional_nested_entity_makes_all_its_fields_optional():
    result = abstract_entity_tree.build(AggregateWithOptionalNested)

    assert result == AbstractEntityTree(
        root=EntityNode(
            name="aggregate_with_optional_nested",
            type=AggregateWithOptionalNested,
            children=(
                FieldNode(name="id", type=int, nullable=False, children=(), is_identity=True),
                ValueObjectNode(
                    name="wallet",
                    type=NestedValueObject,
                    nullable=True,
                    children=(
                        FieldNode(name="amount", type=Decimal, nullable=False, children=(), is_identity=False),
                        FieldNode(name="currency", type=str, nullable=False, children=(), is_identity=False),
                    ),
                ),
            ),
        )
    )
