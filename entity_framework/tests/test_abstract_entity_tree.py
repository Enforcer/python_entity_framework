# import typing
# from decimal import Decimal
# from enum import Enum
# from uuid import UUID
#
# from entity_framework import abstract_entity_tree
# from entity_framework import Entity, Identity, ValueObject
#
#
# class DummyEnum(Enum):
#     FIRST_VALUE = "FIRST_VALUE"
#     ANOTHER_VALUE = "ANOTHER_VALUE"
#
#
# class SimpleFlat(Entity):
#     guid: Identity[UUID]
#     name: typing.Optional[str]
#     score: int
#     enumerated: DummyEnum
#     balance: typing.Optional[Decimal]
#
#
# def test_builds_simple_flat_entity():
#     result = abstract_entity_tree.build(SimpleFlat)
#
#     assert result.fields == {"guid": UUID, "name": str, "score": int, "enumerated": DummyEnum, "balance": Decimal}
#     assert result.identity == ["guid"]
#     assert result.nullables == ["name", "balance"]
#     assert result.nested_lists == {}
#
#
# class NestedValueObject(ValueObject):
#     amount: Decimal
#     currency: str
#
#
# class NestedEntity(Entity):
#     nested_guid: Identity[UUID]
#     name: typing.Optional[str]
#
#
# class SomeAggregate(Entity):
#     guid: Identity[UUID]
#     nested: NestedEntity
#     balance: NestedValueObject
#
#
# def test_builds_aggregate_with_embedded_entity_and_value_object():
#     result = abstract_entity_tree.build(SomeAggregate)
#
#     assert result.fields == {
#         "guid": UUID,
#         "nested_nested_guid": UUID,
#         "nested_name": str,
#         "balance_amount": Decimal,
#         "balance_currency": str,
#     }
#     assert result.identity == ["guid"]
#     assert result.nullables == ["nested_name"]
#     assert result.nested_lists == {}
#
#
# class AggregateWithValueObjectList(Entity):
#     id: Identity[int]
#     wallets: typing.List[NestedValueObject]
#
#
# def test_builds_aggregate_with_list_of_value_objects():
#     result = abstract_entity_tree.build(AggregateWithValueObjectList)
#
#     assert result.fields == {"id": int}
#     assert result.identity == ["id"]
#     assert result.nullables == []
#     assert result.nested_lists == {"wallets": NestedValueObject}
#
#
# class AggregateWithOptionalNested(Entity):
#     id: Identity[int]
#     wallet: typing.Optional[NestedValueObject]
#
#
# def test_optional_nested_entity_makes_all_its_fields_optional():
#     result = abstract_entity_tree.build(AggregateWithOptionalNested)
#
#     assert result.fields == {"id": int, "wallet_amount": Decimal, "wallet_currency": str}
#     assert result.identity == ["id"]
#     assert result.nullables == ["wallet_amount", "wallet_currency"]
#     assert result.nested_lists == {}
