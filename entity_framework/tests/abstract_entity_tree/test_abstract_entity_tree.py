import typing

import pytest

from entity_framework.entity import Entity, Identity, ValueObject
from entity_framework.abstract_entity_tree import AbstractEntityTree, EntityNode, ValueObjectNode, FieldNode


class Skill(ValueObject):
    skill_name: str
    damage: int


class Dragon(Entity):
    name: Identity[str]
    skill: Skill
    age: int


@pytest.fixture()
def tree() -> AbstractEntityTree:
    return AbstractEntityTree(
        root=EntityNode(
            name="dragon",
            type=Dragon,
            children=[
                FieldNode(name="name", type=str, is_identity=True),
                ValueObjectNode(
                    name="skill",
                    type=Skill,
                    children=[FieldNode(name="skill_name", type=str), FieldNode(name="damage", type=int)],
                ),
                FieldNode(name="age", type=int),
            ],
        )
    )


@pytest.fixture()
def dfs_names_order() -> typing.List[str]:
    return ["dragon", "name", "skill", "skill_name", "damage", "age"]


def test_iterates_dfs(tree: AbstractEntityTree, dfs_names_order: typing.List[str]) -> None:
    names = [node.name for node in tree]

    assert names == dfs_names_order
