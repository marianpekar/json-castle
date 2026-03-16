from json_castle import JsonCastle
from dataclasses import dataclass
import os
import json
import tempfile
import unittest
import datetime as dt
from enum import Enum
from typing import Optional, Union

TEST_JSON = {
    "$global_supplies": "Global Supplies",
    "$euro": "Euro",
    "$euro_trail": "${euro} Trail",
    "$number": 4.7,
    "$fo": "fo",
    "name": "Foo",
    "name_with_var": "${fo}o",
    "unit_price": 12.3,
    "quantity_on_hand": 10,
    "ratings": [0, 1.7, 2.2, 3, 4.6, 5],
    "category": "${fo}od",
    "active": True,
    "$bool": True,
    "foreign": "${bool}",
    "elements": ["foo", "foo", "bar", "bar", "fizz"],
    "tags": ["fizz", "buzz"],
    "$bar": "bar",
    "$fizz": "fizz",
    "$buzz": "buzz",
    "elements_with_vars": ["${fo}o", "${bar}"],
    "tags_with_vars": ["${fizz}", "${buzz}"],
    "supplier_name": "${euro_trail}",
    "supplier": {
        "name": "${global_supplies}",
        "country": "USA",
        "rating": "${number}",
        "active": True,
        "elements": ["foo", "foo", "bar", "bar", "fizz"],
        "tags": ["fizz", "buzz"],
        "ratings": [0, 1.7, 2.2, 3, 4.6, 5],
    },
    "supplier2": {
        "name": "${euro_trail}",
        "country": "Germany",
        "rating": "${number}",
        "active": "${bool}",
        "elements_with_vars": ["${fo}o", "${bar}"],
        "tags_with_vars": ["${fizz}", "${buzz}"],
    },
    "suppliers": [
        {
            "name": "Global Supplies",
            "country": "USA",
            "rating": 4.7,
            "active": True,
            "elements": ["foo", "foo", "bar", "bar", "fizz"],
            "tags": ["fizz", "buzz"],
            "ratings": [0, 1.7, 2.2, 3, 4.6, 5],
        },
        {
            "name": "Euro Trade",
            "country": "%COUNTRY%",
            "rating": 4.3,
            "active": False,
        },
        {
            "name": "${global_supplies}",
            "country": "Germany",
            "rating": "${number}",
            "active": "${bool}",
            "elements_with_vars": ["${fo}o", "${bar}"],
            "tags_with_vars": ["${fizz}", "${buzz}"],
        },
        {
            "name": "${euro_trail}",
            "country": "Germany",
            "rating": 4.3,
        },
    ],
    "system": "%SYSTEM_ENV_VAR%",
    "path": "%ROOT_PATH%/src",
    "expression": "{{1+1}}",
    "expressions": [
        "1+1={{1+1}}",
        "{{__import__('datetime').datetime.today().strftime('%B %d, %Y')}}",
        "{{${number}+1}}",
    ],
}


class ItemCategory(Enum):
    FOOD = "food"
    TOOL = "tool"
    OTHER = "other"


@dataclass
class Supplier:
    name: str
    country: str
    rating: float
    active: bool = False
    elements: list[str] = None
    tags: tuple[str, ...] = ()
    elements_with_vars: list[str] = None
    tags_with_vars: tuple[str, ...] = ()
    ratings: list[int] = None


@dataclass
class InventoryItem:
    name: str
    name_with_var: str
    unit_price: float
    quantity_on_hand: int = 0
    active: bool = True
    foreign: bool = False
    discount: Optional[float] = None
    elements: list[str] = None
    elements_with_dups: list[str] = None
    tags: tuple[str, ...] = ()
    elements_with_vars: list[str] = None
    tags_with_vars: tuple[str, ...] = ()
    ratings: list[int] = None
    category: ItemCategory = ItemCategory.OTHER
    supplier_name: str = None
    supplier: Optional[Supplier] = None
    supplier2: Optional[Supplier] = None
    suppliers: list[Supplier] = None
    metadata: dict[str, int] = None
    related_items: dict[str, InventoryItem] = None
    mixed_value: Union[int, str] = None
    system: str = None
    path: str = None
    expression: str = None
    expressions: list[str] = None


def write_temp_json(data):
    tmp = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    json.dump(data, tmp)
    tmp.close()
    return tmp.name


class BaseTest(unittest.TestCase):
    
    def setUp(self):
        self.path = write_temp_json(TEST_JSON)

    def _load(self, **kwargs):
        return JsonCastle.load_from_file(InventoryItem, self.path, **kwargs)


class BasicLoadTests(BaseTest):

    def test_basic_fields(self):
        item = self._load()
        self.assertEqual(item.name, "Foo")
        self.assertEqual(item.unit_price, 12.3)
        self.assertEqual(item.quantity_on_hand, 10)
        self.assertEqual(item.active, True)

    def test_list_and_tuple_coercion(self):
        item = self._load()
        self.assertEqual(item.elements, ["foo", "foo", "bar", "bar", "fizz"])
        self.assertEqual(item.tags, ("fizz", "buzz"))

    def test_enum_coercion(self):
        item = self._load()
        self.assertEqual(item.category, ItemCategory.FOOD)

    def test_nested_object(self):
        item = self._load()
        self.assertEqual(item.supplier.country, "USA")
        self.assertEqual(item.supplier.elements, ["foo", "foo", "bar", "bar", "fizz"])
        self.assertEqual(item.supplier.tags, ("fizz", "buzz"))

    def test_list_of_objects(self):
        item = self._load()
        self.assertEqual(item.suppliers[0].country, "USA")
        self.assertEqual(item.suppliers[0].elements, ["foo", "foo", "bar", "bar", "fizz"])
        self.assertEqual(item.suppliers[0].tags, ("fizz", "buzz"))


class VariableSubstitutionTests(BaseTest):

    def test_full_variable_substitution(self):
        item = self._load()
        self.assertEqual(item.supplier.name, "Global Supplies")
        self.assertEqual(item.supplier.rating, 4.7)
        self.assertEqual(item.foreign, True)

    def test_partial_variable_substitution(self):
        item = self._load()
        self.assertEqual(item.name_with_var, "foo")

    def test_partial_variable_substitution_in_enum(self):
        item = self._load()
        self.assertEqual(item.category, ItemCategory.FOOD)

    def test_variable_in_list(self):
        item = self._load()
        self.assertEqual(item.elements_with_vars, ["foo", "bar"])
        self.assertEqual(item.tags_with_vars, ("fizz", "buzz"))

    def test_variable_in_nested_object(self):
        item = self._load()
        self.assertEqual(item.suppliers[2].name, "Global Supplies")
        self.assertEqual(item.suppliers[2].rating, 4.7)
        self.assertEqual(item.suppliers[2].elements_with_vars, ["foo", "bar"])
        self.assertEqual(item.suppliers[2].tags_with_vars, ("fizz", "buzz"))

    def test_chained_variable(self):
        item = self._load()
        self.assertEqual(item.supplier_name, "Euro Trail")

    def test_chained_variable_in_nested_object(self):
        item = self._load()
        self.assertEqual(item.supplier2.name, "Euro Trail")

    def test_chained_variable_in_list(self):
        item = self._load()
        self.assertEqual(item.suppliers[3].name, "Euro Trail")

    def test_environment_variable_full(self):
        os.environ["SYSTEM_ENV_VAR"] = "Linux"
        item = self._load()
        self.assertEqual(item.system, "Linux")

    def test_environment_variable_partial(self):
        os.environ["ROOT_PATH"] = "dev/ci"
        item = self._load()
        self.assertEqual(item.path, "dev/ci/src")

    def test_environment_variable_in_list(self):
        os.environ["COUNTRY"] = "Germany"
        item = self._load()
        self.assertEqual(item.suppliers[1].country, "Germany")


class KwargsOverrideTests(BaseTest):

    def test_override_scalar_fields(self):
        item = self._load(unit_price="99.9", active="false", foreign="false")
        self.assertEqual(item.unit_price, 99.9)
        self.assertEqual(item.active, False)
        self.assertEqual(item.foreign, False)

    def test_override_list_elements_by_index(self):
        item = self._load(**{"elements[0]": "Fizz", "elements_with_vars[1]": "Foo"})
        self.assertEqual(item.elements[0], "Fizz")
        self.assertEqual(item.elements_with_vars[1], "Foo")

    def test_override_nested_object_fields(self):
        item = self._load(**{"supplier.country": "Japan", "supplier.active": "False"})
        self.assertEqual(item.supplier.country, "Japan")
        self.assertEqual(item.supplier.active, False)

    def test_override_list_of_objects_by_index(self):
        item = self._load(**{
            "suppliers[0].country": "Japan",
            "suppliers[0].active": "false",
            "suppliers[2].active": "false",
        })
        self.assertEqual(item.suppliers[0].country, "Japan")
        self.assertEqual(item.suppliers[0].active, False)
        self.assertEqual(item.suppliers[2].active, False)


class CollectionAddTests(BaseTest):

    def test_add_to_list(self):
        item = self._load(**{"+elements": "fizz"})
        self.assertEqual(len(item.elements), 6)
        self.assertEqual(item.elements[5], "fizz")

    def test_add_to_tuple(self):
        item = self._load(**{"+tags": "bar"})
        self.assertEqual(len(item.tags), 3)
        self.assertEqual(item.tags[2], "bar")

    def test_add_object_to_list(self):
        item = self._load(**{
            "+suppliers": {
                "name": "New Supplier",
                "country": "Japan",
                "rating": 4.9,
                "active": True,
            }
        })
        self.assertEqual(len(item.suppliers), 5)
        new = item.suppliers[4]
        self.assertEqual(new.name, "New Supplier")
        self.assertEqual(new.country, "Japan")
        self.assertEqual(new.rating, 4.9)
        self.assertEqual(new.active, True)


class CollectionRemoveByIndexTests(BaseTest):
    """Remove items via index / slice notation."""

    index_cases = [
        ("~suppliers[0]",      lambda i: (len(i.suppliers) == 3 and i.suppliers[0].name == "Euro Trade")),
        ("~tags[1]",           lambda i: (len(i.tags) == 1 and i.tags[0] == "fizz")),
        ("~elements[1:]",      lambda i: i.elements == ["foo"]),
        ("~elements[:2]",      lambda i: i.elements == ["bar", "fizz"]),
        ("~elements[1:3]",     lambda i: i.elements == ["foo", "fizz"]),
        ("~elements[:]",       lambda i: len(i.elements) == 0),
        ("~tags[:]",           lambda i: len(i.tags) == 0),
        ("~!suppliers[0]",     lambda i: (len(i.suppliers) == 1 and i.suppliers[0].name == "Global Supplies")),
        ("~!elements[1:]",     lambda i: i.elements == ["foo", "bar", "bar", "fizz"]),
        ("~!elements[:2]",     lambda i: i.elements == ["foo", "foo", "bar"]),
        ("~!elements[1:3]",    lambda i: i.elements == ["foo", "bar", "bar"]),
    ]

    def test_remove_by_index(self):
        for kwarg, check in self.index_cases:
            with self.subTest(kwarg=kwarg):
                item = self._load(**{kwarg: ""})
                self.assertTrue(check(item), f"Failed for kwarg={kwarg!r}")

    def test_remove_by_index_nested(self):
        item = self._load(**{"~supplier.elements[1:]": ""})
        self.assertEqual(item.supplier.elements, ["foo"])

    def test_remove_by_index_in_list(self):
        item = self._load(**{"~suppliers[0].elements[:2]": ""})
        self.assertEqual(item.suppliers[0].elements, ["bar", "fizz"])


class CollectionRemoveByValueTests(BaseTest):
    """Remove items by exact value, regex, or numeric comparison."""

    string_cases = [
        ("~elements",    "foo",          ["foo", "bar", "bar", "fizz"]),
        ("~tags",        "fizz",         ("buzz",)),
        ("~~elements",   "bar",          ["foo", "foo", "fizz"]),
        ("~elements",    r"\bf\w*",      ["foo", "bar", "bar", "fizz"]),
        ("~~elements",   r"\bf\w*",      ["bar", "bar"]),
        ("~!elements",   "foo",          ["foo"]),
        ("~~!elements",  "bar",          ["bar", "bar"]),
        ("~~!elements",  r"\bf\w*",      ["foo", "foo", "fizz"]),
    ]

    numeric_cases = [
        ("~ratings",  "3",        [0, 1.7, 2.2, 4.6, 5],   [3]),
        ("~ratings",  "1.7",      [0, 2.2, 3, 4.6, 5],     [1.7]),
        ("~ratings",  "lt3",      [3, 4.6, 5],             [0, 1.7, 2.2]),
        ("~ratings",  "lte3",     [4.6, 5],                [0, 1.7, 2.2, 3]),
        ("~ratings",  "gt3",      [0, 1.7, 2.2, 3],        [4.6, 5]),
        ("~ratings",  "gte3",     [0, 1.7, 2.2],           [3, 4.6, 5]),
        ("~ratings",  "gt1&lt4",  [0, 4.6, 5],             [1.7, 2.2, 3]),
    ]

    def test_remove_by_string_value_or_regex(self):
        for kwarg, val, expected in self.string_cases:
            with self.subTest(kwarg=kwarg, val=val):
                item = self._load(**{kwarg: val})
                result = item.elements if "elements" in kwarg else item.tags
                self.assertEqual(result, expected)

    def test_remove_by_numeric_filter(self):
        for kwarg, val, expected, expected_neg in self.numeric_cases:
            neg_kwarg = kwarg.replace("~", "~!", 1)
            with self.subTest(kwarg=kwarg, val=val):
                item = self._load(**{kwarg: val})
                self.assertEqual(item.ratings, expected)
            with self.subTest(kwarg=neg_kwarg, val=val):
                item = self._load(**{neg_kwarg: val})
                self.assertEqual(item.ratings, expected_neg)

    def test_remove_by_value_nested(self):
        item = self._load(**{"~supplier.elements": "foo"})
        self.assertEqual(item.supplier.elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_by_value_tuple_nested(self):
        item = self._load(**{"~supplier.tags": "fizz"})
        self.assertEqual(item.supplier.tags, ("buzz",))

    def test_remove_by_value_in_list_of_objects(self):
        item = self._load(**{"~suppliers[0].elements": "foo"})
        self.assertEqual(item.suppliers[0].elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_by_value_tuple_in_list_of_objects(self):
        item = self._load(**{"~suppliers[0].tags": "fizz"})
        self.assertEqual(item.suppliers[0].tags, ("buzz",))

    def test_remove_numeric_nested(self):
        item = self._load(**{"~supplier.ratings": "1.7"})
        self.assertEqual(item.supplier.ratings, [0, 2.2, 3, 4.6, 5])

    def test_remove_numeric_lt_nested(self):
        item = self._load(**{"~supplier.ratings": "lt3"})
        self.assertEqual(item.supplier.ratings, [3, 4.6, 5])

    def test_remove_numeric_in_list_of_objects(self):
        item = self._load(**{"~suppliers[0].ratings": "1.7"})
        self.assertEqual(item.suppliers[0].ratings, [0, 2.2, 3, 4.6, 5])

    def test_remove_numeric_in_list_of_objects_negate(self):
        item = self._load(**{"~!suppliers[0].ratings": "1.7"})
        self.assertEqual(item.suppliers[0].ratings, [1.7])

    def test_remove_numeric_gt_in_list_of_objects(self):
        item = self._load(**{"~suppliers[0].ratings": "gt3"})
        self.assertEqual(item.suppliers[0].ratings, [0, 1.7, 2.2, 3])

    def test_remove_numeric_compound_in_list_of_objects(self):
        item = self._load(**{"~suppliers[0].ratings": "gt1.7&lte4.6"})
        self.assertEqual(item.suppliers[0].ratings, [0, 1.7, 5])

    def test_remove_numeric_compound_in_list_of_objects_negate(self):
        item = self._load(**{"~!suppliers[0].ratings": "gt1.7&lte4.6"})
        self.assertEqual(item.suppliers[0].ratings, [2.2, 3, 4.6])


class ExpressionEvalTests(BaseTest):

    def test_simple_expression(self):
        item = self._load()
        self.assertEqual(item.expression, "2")

    def test_expression_embedded_in_string(self):
        item = self._load()
        self.assertEqual(item.expressions[0], "1+1=2")

    def test_expression_with_stdlib(self):
        item = self._load()
        self.assertEqual(item.expressions[1], dt.date.today().strftime("%B %d, %Y"))

    def test_expression_with_variable(self):
        item = self._load()
        self.assertEqual(item.expressions[2], "5.7")


if __name__ == "__main__":
    unittest.main()