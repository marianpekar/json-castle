from json_castle import JsonCastle
from dataclasses import dataclass
import os
import json
import tempfile
import unittest
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

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
    "category": "${fo}od",
    "active": True,
    "$bool": True,
    "foreign": "${bool}",
    "elements": [ "foo", "bar" ],
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
        "elements": [ "foo", "bar" ],
        "tags": [ "fizz", "buzz" ],
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
            "elements": [ "foo", "bar" ],
            "tags": [ "fizz", "buzz" ],
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
    "path": "%ROOT_PATH%/src"
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
    elements: List[str] = None
    tags: Tuple[str, ...] = ()
    elements_with_vars: List[str] = None
    tags_with_vars: Tuple[str, ...] = ()

@dataclass
class InventoryItem:
    name: str
    name_with_var: str
    unit_price: float
    quantity_on_hand: int = 0
    active: bool = True
    foreign: bool = False
    discount: Optional[float] = None
    elements: List[str] = None
    tags: Tuple[str, ...] = ()
    elements_with_vars: List[str] = None
    tags_with_vars: Tuple[str, ...] = ()
    ratings: List[int] = None
    category: ItemCategory = ItemCategory.OTHER
    supplier_name: str = None
    supplier: Optional[Supplier] = None
    supplier2: Optional[Supplier] = None
    suppliers: List[Supplier] = None
    metadata: Dict[str, int] = None
    related_items: Dict[str, InventoryItem] = None
    mixed_value: Union[int, str] = None
    system: str = None
    path: str = None

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
        self.assertEqual(item.elements, ["foo", "bar"])
        self.assertEqual(item.tags, ("fizz", "buzz"))
        self.assertEqual(item.suppliers[0].country, "USA")
        self.assertEqual(item.suppliers[0].elements, ["foo", "bar"])
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
        self.assertEqual(len(item.elements), 3)
        self.assertEqual(item.elements[2], "fizz")

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

    def test_remove_tuple_item(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~tags[1]": ""}
        )
        self.assertEqual(len(item.tags), 1)
        self.assertEqual(item.tags[0], "fizz")

    def test_remove_list_item_by_val(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~elements": "foo"}
        )
        self.assertEqual(len(item.elements), 1)
        self.assertEqual(item.elements[0], "bar")

    def test_remove_tuple_item_by_val(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~tags": "fizz"}
        )
        self.assertEqual(len(item.tags), 1)
        self.assertEqual(item.tags[0], "buzz")

    def test_remove_list_item_by_val_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.elements": "foo"}
        )
        self.assertEqual(len(item.supplier.elements), 1)
        self.assertEqual(item.supplier.elements[0], "bar")

    def test_remove_tuple_item_by_val_nested(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~supplier.tags": "fizz"}
        )
        self.assertEqual(len(item.supplier.tags), 1)
        self.assertEqual(item.supplier.tags[0], "buzz")

    def test_remove_list_item_by_val_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].elements": "foo"}
        )
        self.assertEqual(len(item.suppliers[0].elements), 1)
        self.assertEqual(item.suppliers[0].elements[0], "bar")

    def test_remove_tuple_item_by_val_in_list(self):
        path = write_temp_json(TEST_JSON)
        item = JsonCastle.load_from_file(
            InventoryItem,
            path,
            **{"~suppliers[0].tags": "fizz"}
        )
        self.assertEqual(len(item.suppliers[0].tags), 1)
        self.assertEqual(item.suppliers[0].tags[0], "buzz")