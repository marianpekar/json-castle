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
    "ratings": [ 0, 1.7, 2.2, 3, 4.6, 5 ],
    "category": "${fo}od",
    "active": True,
    "$bool": True,
    "foreign": "${bool}",
    "elements": [ "foo", "foo", "bar", "bar", "fizz" ],
    "tags": [ "fizz", "buzz" ],
    "$bar": "bar",
    "$fizz": "fizz",
    "$buzz": "buzz",
    "elements_with_vars": [ "${fo}o", "${bar}" ],
    "tags_with_vars": [ "${fizz}", "${buzz}" ],
    "supplier_name": "${euro_trail}",
    "supplier": {
        "name": "${global_supplies}",
        "country": "USA",
        "rating": "${number}",
        "active": True,
        "elements": [ "foo", "foo", "bar", "bar", "fizz" ],
        "tags": [ "fizz", "buzz" ],
        "ratings": [ 0, 1.7, 2.2, 3, 4.6, 5 ],
    },
    "supplier2": {
        "name": "${euro_trail}",
        "country": "Germany",
        "rating": "${number}",
        "active": "${bool}",
        "elements_with_vars": [ "${fo}o", "${bar}" ],
        "tags_with_vars": [ "${fizz}", "${buzz}" ],
    },
    "suppliers": [
        {
            "name": "Global Supplies",
            "country": "USA",
            "rating": 4.7,
            "active": True,
            "elements": [ "foo", "foo", "bar", "bar", "fizz" ],
            "tags": [ "fizz", "buzz" ],
            "ratings": [ 0, 1.7, 2.2, 3, 4.6, 5 ]
        },
        {
            "name": "Euro Trade",
            "country": "%COUNTRY%",
            "rating": 4.3,
            "active": False
        },
        {
            "name": "${global_supplies}",
            "country": "Germany",
            "rating": "${number}",
            "active": "${bool}",
            "elements_with_vars": [ "${fo}o", "${bar}" ],
            "tags_with_vars": [ "${fizz}", "${buzz}" ],
        },
        {
            "name": "${euro_trail}",
            "country": "Germany",
            "rating": 4.3
        },
    ],
    "system": "%SYSTEM_ENV_VAR%",
    "path": "%ROOT_PATH%/src",
    "expression": "{{1+1}}",
    "expressions": [ 
        "1+1={{1+1}}",
        "{{__import__('datetime').datetime.today().strftime('%B %d, %Y')}}",
        "{{${number}+1}}"
    ]
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

class UnitTests(unittest.TestCase):

    def test_basic_load(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path)
        self.assertEqual(item.name, "Foo")
        self.assertEqual(item.category, ItemCategory.FOOD)
        self.assertEqual(item.active, True)
        self.assertEqual(item.elements, ["foo", "foo", "bar", "bar", "fizz"])
        self.assertEqual(item.tags, ("fizz", "buzz"))
        self.assertEqual(item.suppliers[0].country, "USA")
        self.assertEqual(item.suppliers[0].elements, ['foo', 'foo', 'bar', 'bar', 'fizz'])
        self.assertEqual(item.suppliers[0].tags, ("fizz", "buzz"))

    def test_kwargs_override(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path, 
                                         unit_price="99.9", 
                                         active="false", 
                                         foreign="false", 
                                         **{"elements[0]": "Fizz", 
                                            "elements_with_vars[1]": "Foo"},)
        self.assertEqual(item.unit_price, 99.9)
        self.assertEqual(item.active, False)
        self.assertEqual(item.foreign, False)
        self.assertEqual(item.elements[0], "Fizz")
        self.assertEqual(item.elements_with_vars[1], "Foo")

    def test_kwargs_override_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"supplier.country": "Japan", 
               "supplier.active": "false"}, 
        )
        self.assertEqual(item.supplier.country, "Japan")
        self.assertEqual(item.supplier.active, False)

    def test_kwargs_override_list_items(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"suppliers[0].country": "Japan",
               "suppliers[0].active": "false",
               "suppliers[2].active": "false"}
        )
        self.assertEqual(item.suppliers[0].country, "Japan")
        self.assertEqual(item.suppliers[0].active, False)
        self.assertEqual(item.suppliers[2].active, False)

    def test_variable_substitutions(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path)
        self.assertEqual(item.supplier.name, "Global Supplies")
        self.assertEqual(item.foreign, True)
        self.assertEqual(item.supplier.rating, 4.7)
        self.assertEqual(item.elements_with_vars, ["foo", "bar"])
        self.assertEqual(item.tags_with_vars, ("fizz", "buzz"))

    def test_variable_substitutions_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path)
        self.assertEqual(item.suppliers[2].name, "Global Supplies")
        self.assertEqual(item.suppliers[2].rating, 4.7)
        self.assertEqual(item.suppliers[2].elements_with_vars, ["foo", "bar"])
        self.assertEqual(item.suppliers[2].tags_with_vars, ("fizz", "buzz"))

    def test_partial_variable_substitution(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path)
        self.assertEqual(item.name_with_var, "foo")

    def test_partial_variable_substitution_in_enum(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path)
        self.assertEqual(item.category, ItemCategory.FOOD)

    def test_environment_variable_substitution(self):
        path = write_temp_json(TEST_JSON)
        os.environ["SYSTEM_ENV_VAR"] = "Linux"
        item = JsonCastle().load_from_file(InventoryItem, path)
        self.assertEqual(item.system, "Linux")

    def test_partial_environment_variable_substitution(self):
        path = write_temp_json(TEST_JSON)
        os.environ["ROOT_PATH"] = "dev/cj"
        item = JsonCastle().load_from_file(InventoryItem, path)
        self.assertEqual(item.path, "dev/cj/src")

    def test_environment_variable_substitution_in_list(self):
        path = write_temp_json(TEST_JSON)
        os.environ["COUNTRY"] = "Germany"
        item = JsonCastle().load_from_file(InventoryItem, path)
        self.assertEqual(item.suppliers[1].country, "Germany")

    def test_variable_in_variable(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle().load_from_file(InventoryItem, path)
        self.assertEqual(item.supplier_name, "Euro Trail")
    
    def test_variable_in_variable_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle().load_from_file(InventoryItem, path)
        self.assertEqual(item.supplier2.name, "Euro Trail")

    def test_variable_in_variable_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle().load_from_file(InventoryItem, path)
        self.assertEqual(item.suppliers[3].name, "Euro Trail")

    def test_add_list_item(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"+elements": "fizz"}
        )
        self.assertEqual(len(item.elements), 6)
        self.assertEqual(item.elements[5], "fizz")

    def test_add_tupple_item(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"+tags": "bar"}
        )
        self.assertEqual(len(item.tags), 3)
        self.assertEqual(item.tags[2], "bar")

    def test_add_custom_item_from_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{
                "+suppliers": {
                    "name": "New Supplier",
                    "country": "Japan",
                    "rating": 4.9,
                    "active": True
                }
            }
        )
        self.assertEqual(len(item.suppliers), 5)
        self.assertEqual(item.suppliers[4].name, "New Supplier")
        self.assertEqual(item.suppliers[4].country, "Japan")
        self.assertEqual(item.suppliers[4].rating, 4.9)
        self.assertEqual(item.suppliers[4].active, True)

    def test_remove_custom_list_item(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0]": ""}
        )
        self.assertEqual(len(item.suppliers), 3)
        self.assertEqual(item.suppliers[0].name, "Euro Trade")

    def test_remove_custom_list_item_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!suppliers[0]": ""}
        )
        self.assertEqual(len(item.suppliers), 1)
        self.assertEqual(item.suppliers[0].name, "Global Supplies")

    def test_remove_tuple_item(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~tags[1]": ""}
        )
        self.assertEqual(len(item.tags), 1)
        self.assertEqual(item.tags[0], "fizz")

    def test_remove_list_items_by_range_from_left(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements[1:]": ""}
        )
        self.assertEqual(item.elements, ["foo"])

    def test_remove_list_items_by_range_from_left_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!elements[1:]": ""}
        )
        self.assertEqual(item.elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_list_items_by_range_from_right(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements[:2]": ""}
        )
        self.assertEqual(item.elements, [ "bar", "fizz" ])

    def test_remove_list_items_by_range_from_right_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!elements[:2]": ""}
        )
        self.assertEqual(item.elements, [ "foo", "foo", "bar" ])
    
    def test_remove_list_items_by_range(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements[1:3]": ""}
        )
        self.assertEqual(len(item.elements), 2)
        self.assertEqual(item.elements, [ "foo", "fizz" ])

    def test_remove_list_items_by_range_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!elements[1:3]": ""}
        )
        self.assertEqual(item.elements, [ "foo", "bar", "bar" ])

    def test_remove_all_list_items_by_range(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements[:]": ""}
        )
        self.assertEqual(len(item.elements), 0)

    def test_remove_list_items_by_range_from_left_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.elements[1:]": ""}
        )
        self.assertEqual(item.supplier.elements, ["foo"])

    def test_remove_list_items_by_range_from_right_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].elements[:2]": ""}
        )
        self.assertEqual(item.suppliers[0].elements, [ "bar", "fizz" ])

    def test_remove_list_item_by_val(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements": "foo"}
        )
        self.assertEqual(item.elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_list_item_by_val_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!elements": "foo"}
        )
        self.assertEqual(item.elements, [ "foo" ])

    def test_remove_list_item_by_regex(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements": r"\bf\w*"}
        )
        self.assertEqual(item.elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_all_list_items_by_val(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~~elements": "bar"}
        )
        self.assertEqual(item.elements, ["foo", "foo", "fizz"])

    def test_remove_all_list_items_by_val_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~~!elements": "bar"}
        )
        self.assertEqual(item.elements, [ "bar", "bar" ])

    def test_remove_all_list_items_by_regex(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~~elements": r"\bf\w*"}
        )
        self.assertEqual(item.elements, ["bar", "bar"])

    def test_remove_all_list_items_by_regex_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~~!elements": r"\bf\w*"}
        )
        self.assertEqual(item.elements, [ "foo", "foo", "fizz" ])

    def test_remove_tuple_item_by_val(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~tags": "fizz"}
        )
        self.assertEqual(item.tags, ("buzz",))

    def test_remove_all_tuple_items(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~tags[:]": ""}
        )
        self.assertEqual(len(item.tags), 0)

    def test_remove_list_item_by_val_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.elements": "foo"}
        )
        self.assertEqual(item.supplier.elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_tuple_item_by_val_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.tags": "fizz"}
        )
        self.assertEqual(item.supplier.tags, ("buzz",))


    def test_remove_list_item_by_val_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].elements": "foo"}
        )
        self.assertEqual(item.suppliers[0].elements, ["foo", "bar", "bar", "fizz"])

    def test_remove_tuple_item_by_val_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].tags": "fizz"}
        )
        self.assertEqual(item.suppliers[0].tags, ("buzz",))

    def test_evaluate_python_expressions(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(InventoryItem, path)
        self.assertEqual(item.expression, "2")
        self.assertEqual(item.expressions[0], "1+1=2")
        self.assertEqual(item.expressions[1], dt.date.today().strftime("%B %d, %Y"))
        self.assertEqual(item.expressions[2], "5.7")

    def test_remove_list_item_int(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "3"}
        )
        self.assertEqual(item.ratings, [ 0, 1.7, 2.2, 4.6, 5 ])

    def test_remove_list_item_float(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "1.7"}
        )
        self.assertEqual(item.ratings, [ 0, 2.2, 3, 4.6, 5 ])

    def test_remove_list_items_less_than_float(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "lt3"}
        )
        self.assertEqual(item.ratings, [ 3, 4.6, 5 ])

    def test_remove_list_items_less_than_or_equal_float(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "lte3"}
        )
        self.assertEqual(item.ratings, [ 4.6, 5 ])

    def test_remove_list_items_greater_than_float(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "gt3"}
        )
        self.assertEqual(item.ratings, [ 0, 1.7, 2.2, 3 ])

    def test_remove_list_items_greater_than_or_equal_float(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "gte3"}
        )
        self.assertEqual(item.ratings, [ 0, 1.7, 2.2 ])

    def test_remove_list_item_float_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.ratings": "1.7"}
        )
        self.assertEqual(item.supplier.ratings, [ 0, 2.2, 3, 4.6, 5 ])

    def test_remove_list_items_less_than_float_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.ratings": "lt3"}
        )
        self.assertEqual(item.supplier.ratings, [ 3, 4.6, 5 ])

    def test_remove_list_items_float_nested_in_collection(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].ratings": "1.7"}
        )
        self.assertEqual(item.suppliers[0].ratings, [ 0, 2.2, 3, 4.6, 5 ])

    def test_remove_list_items_float_nested_in_collection_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!suppliers[0].ratings": "1.7"}
        )
        self.assertEqual(item.suppliers[0].ratings, [ 1.7 ])

    def test_remove_list_item_greater_than_float_nested_in_collection(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].ratings": "gt3"}
        )
        self.assertEqual(item.suppliers[0].ratings, [ 0, 1.7, 2.2, 3 ])

    def test_remove_list_items_greater_than_and_less_than_float(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~ratings": "gt1&lt4"}
        )
        self.assertEqual(item.ratings, [ 0, 4.6, 5 ])

    def test_remove_list_item_greater_than_and_less_than_or_equal_float_nested_in_collection(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].ratings": "gt1.7&lte4.6"}
        )
        self.assertEqual(item.suppliers[0].ratings, [ 0, 1.7, 5 ])

    def test_remove_list_items_greater_than_and_less_than_float_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!ratings": "gt1&lt4"}
        )
        self.assertEqual(item.ratings, [ 1.7, 2.2, 3 ])

    def test_remove_list_item_greater_than_and_less_than_or_equal_float_nested_in_collection_negate(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~!suppliers[0].ratings": "gt1.7&lte4.6"}
        )
        self.assertEqual(item.suppliers[0].ratings, [ 2.2, 3, 4.6 ])




if __name__ == '__main__':
    unittest.main()