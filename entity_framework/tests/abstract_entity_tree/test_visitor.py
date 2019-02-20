import typing

import pytest

from entity_framework.entity import Entity, Identity, ValueObject
from entity_framework.abstract_entity_tree import (
    AbstractEntityTree,
    EntityNode,
    ValueObjectNode,
    FieldNode,
    Visitor,
    Node,
)


class Scribe(Visitor):
    def __init__(self) -> None:
        self.visits_log: typing.List[typing.Tuple[str, str]] = []

    def visit_field(self, node: "Node") -> None:
        self.visits_log.append(("visit", node.name))

    def leave_field(self, node: "Node") -> None:
        self.visits_log.append(("leave", node.name))

    visit_entity = visit_value_object = visit_list_of_entities = visit_list_of_value_objects = visit_field
    leave_entity = leave_value_object = leave_list_of_entities = leave_list_of_value_objects = leave_field


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


def test_iterates_tree(tree: AbstractEntityTree) -> None:
    visitor = Scribe()
    visitor.traverse_from(tree.root)

    assert visitor.visits_log == [
        ("visit", "dragon"),
        ("visit", "name"),
        ("leave", "name"),
        ("visit", "skill"),
        ("visit", "skill_name"),
        ("leave", "skill_name"),
        ("visit", "damage"),
        ("leave", "damage"),
        ("leave", "skill"),
        ("visit", "age"),
        ("leave", "age"),
        ("leave", "dragon"),
    ]
