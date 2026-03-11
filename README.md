# JsonCastle

JsonCastle is a Python module built on top of the native json module for deserialization from JSON to data classes with additional support for:

- nested objects
- JSON variables
- environment variables
- arbitrary Python expressions
- post-load overrides, including overriding, adding, and removing collection elements via special [CLI Overrides Syntax](#cli-overrides-syntax) like `node.next_node.number=2`, `~node.tags[0]`, `~node.tags[1:3]`, `+node.next_node.tags=foo`, `~node.next_node.tags=buzz`, etc.

With these features, you might find it especially useful in CI/CD pipelines.

## Getting Started

Imagine you have a JSON configuration file for an automated process, but you want to run this process with slightly different variants of this file. Typically, you'd end up with multiple very similar configuration files, or you'd create an ad-hoc solution that would allow you to override certain parameters via CLI arguments. JsonCastle gives you such a solution out of the box for all properties of your data scheme, even for those in nested objects.

Since native json doesn't support variables, such configuration files might have a lot of repeated strings. Editing such files can be tedious and error-prone. You write a JSON file with variables and environment variables as the following example:

```json
{
    "$home_path": "%HOME%",
    "$package_path": "${home_path}debug",
    "exe_path": "${package_path}/mytool.exe",
    "node": {
        "number": 0,
        "tags": ["foo", "bar"],
        "next_node": {
            "number": 1,
            "tags": ["fizz", "buzz"]
        }
    },
    "$pi": 3.14159,
    "expressions": [
        "1+1={{1+1}}",
        "{{__import__('datetime').datetime.today().strftime('%B %d, %Y')}}",
        "{{${pi}*2}}"
    ]
}
```

Assuming the `HOME` environment variable is set, for example, to `C:/users/cicd/`, then the value of the `$package_path` variable will be expanded from `${home_path}debug` to `C:/users/cicd/debug`, and the value of `exe_path` will be `C:/users/cicd/debug/mytool.exe`.

In Python, you'd define your data classes that match the scheme:

```python
from dataclasses import dataclass

@dataclass
class Cfg:
    exe_path: str = None
    node: Node = None
    expressions: list[str] = None

@dataclass
class Node:
    number: int
    tags: list[str]
    processed: False
    next_node: Node = None
```

Now you can use the `JsonCastle.load_from_file` method to read and parse `example.json` and get an instance of the `Cfg` class:

```python
from pprint import pprint
import sys

from json_castle import JsonCastle

cfg = JsonCastle.load_from_file(Cfg, "example.json", **JsonCastle.parse_args(sys.argv))
pprint(cfg)
```

If you run the Python script without any arguments, you’d see cfg printed as expected:

```txt
Cfg(exe_path='C:/users/cicd/debug/mytool.exe',
    node={'next_node': {'number': 1, 'tags': ['fizz', 'buzz']},
          'number': 0,
          'tags': ['foo', 'bar']},
    expressions=['1+1=2', 'March 07, 2026', '6.28318'])
```

However, by passing `**JsonCastle.parse_args(sys.argv)` as the third argument, you can override any values post-load via CLI. Running the script again with the arguments `node.number=1 ~node.tags[0] node.next_node.number=2 +node.next_node.tags=foo ~node.next_node.tags=buzz` will give you a cfg instance like this:

```txt
Cfg(exe_path='C:/users/cicd/debug/mytool.exe',
    node={'next_node': {'number': 2, 'tags': ['fizz', 'foo']},
          'number': 1,
          'tags': ['bar']},
    expressions=['1+1=2', 'March 07, 2026', '6.28318'])
```

If you want to deserialize your JSON from a string stream, you can use the static method `load(cls, stream: IO[str], **kwargs)`, the usage is the same as of the `load_from_file(cls, path: str, **kwargs)` in the example above, but you provide your stream as the second argument instead of filepath.

Optionally, you can pass a second parameter to the `JsonCastle.parse_args` method to set the index from which arguments should be parsed, so you can reserve the preceding arguments for something else, i.e., you can use the first CLI argument to specify a path to a JSON file and start parsing overrides from the second one like this:

```python
cfg = JsonCastle.load_from_file(Cfg, sys.argv[1], **JsonCastle.parse_args(sys.argv, 2))
```

## CLI Overrides Syntax

Although some of the syntax for post-load overrides via the CLI was introduced already in the [Getting Started](#getting-started) section, here's an overview of all options with examples.

### Basic Syntax

`JsonCastle.parse_args` method accepts a list of strings, where each element is a `key=value` pair except the one for removing an item by index, that only has a key, in which case, in the dictionary the method returns, the value is `None`.

Of course, you don't have to use this method and construct a dictionary by yourself instead; the `JsonCastle.parse_args` just provides you a convenient way for post-load overriding via CLI, which is particularly useful in CI/CD pipelines. Here are some examples of CLI args for overriding top-level pairs:

```txt
age=27 name=John full_name="John Smith" active=true balance=123.45
```

### Nested Objects

If you need to override a nested value, you specify a path, separating objects with `.`, as you can see in the [Getting Started](#getting-started). The following example shows how to override several pairs nested in the `person` object.

```txt
person.age=27 person.name=John person.full_name="John Smith" person.active=true person.balance=123.45
```

### Working with Collections

When it comes to collections, you can change, add, or remove an item as well. If the collection is a nested object, the rules are the same as described in the [Nested Objects](#nested-objects) section.

#### Overriding an Item

To override an item, you provide a path to the collection, in square brackets an index of the item you wish to override, and a new value on the right side of the `=` symbol. The following example shows how to change the value of the first element of the `tags` collection nested in the `page` object to `programming`.

```txt
page.tags[0]=programming
```

#### Adding a new Item

When you wish to add a new item to a collection, you prefix the `key=value` pair with a `+` symbol. The following example shows how to add a new value of `python` to the `tags` collection nested in the `page` object.

```txt
+page.tags=python
```

#### Removing an Item at Index

If you wish to remove an item at specific index, you prefix a path to the collection with index in square brackets of the element you wish to remove with the `~` symbol. The following example shows how to remove the second item from the tags collection nested in the page object.

```txt
~page.tags[1]
```

If any items follow the removed one, they will be pushed down, and the new length of the collection will be n-1.

#### Removing Items by Range

You can also remove multiple items by using a slice syntax. The following examples show how to remove all elements except the first one in the `tags` collection nested in the `page` object, how to remove all but the last two elements, and how to remove elements at index 1, 2, and 3, and all elements respectively.

```txt
~page.tags[1:]
~page.tags[:2]
~page.tags[1:3]
~page.tags[:]
```

#### Removing an Item by Value (Supports Regular Expressions)

If you wish to remove an item of a specific value, instead of the index as described in Removing an Item by Index, you provide a key=value pair prefixed with ~. The following example shows how to remove an item with a value of `programming` from the tags collection nested in the page object.

```txt
~page.tags=programming
```

If there is more than one occurrence of the `programming` string in the collection, only the first one will be removed. If you want to remove **all** occurrences, use `~~` instead of just one `~`:

```txt
~~page.tags=programming
```

The value can be a regex. The following example shows how to remove all items with a value of a single word that starts with `pro`:

```txt
~~page.tags="\bpro\w*"
```

#### Removing Numerical Items by Condition

From numerical collections, you can remove all values that are less than (`lt`), less than or equal (`lte`), greater than (`gt`), or greater than or equal (`gte`) to a value on the right side of the argument. The following examples show how to remove values less than, less than or equal, greater than, and greater than or equal to `3` from the `ratings` collection, which itself is a property of the first supplier in the `suppliers` collection.

```txt
~suppliers[0].ratings=lt3
~suppliers[0].ratings=lte3
~suppliers[0].ratings=gt3
~suppliers[0].ratings=gte3
```

Additionally, you can join conditions together with the `&` operator. The following example shows how to remove all items from the `ratings` collection with values greater than `1.7` and less than or equal to `4.6` (i.e., `[ 0, 1.7, 2.2, 3, 4.6, 5 ] -> [ 0, 1.7, 5 ]`).

```txt
~ratings=gt1.7&lte4.6
```

## Python Expressions

Any string in JSON value between `{{` and `}}` symbols will be treated as an arbitrary Python expression and replaced by the result of [eval()](https://docs.python.org/3/library/functions.html#eval) function converted back to a string.

See the `"expressions"` collection at the bottom of the example JSON in [Getting Started](#getting-started) section.

## Unit Tests

Unit Tests are not just a great way to ensure nothing is broken when a new feature is added, but also for implementing new features using TDD, which is the recommended way for extending this library. These tests can also serve as an overview of what the library is capable of. You can find all tests in the `tests/test_json_castle.py` file.

## Future Ideas

* Add support for conditionals and loops in JSON.
* ~~Add mathematical expressions in JSON.~~ ✅
* Extend the `parse_args` method to allow adding a custom object to a collection.
* ~~Add regex support for removing items by value.~~ ✅
* ~~When removing an item from a collection by value, let the user decide whether they want to remove just one or all items that match the value (`~page.tags=programming` removes the first; `~!page.tags=programming` removes all).~~ ✅
* ~~Add support for removing items from a numerical collection by conditions `>`, `<`, `<=` , or `=>`.~~ ✅
* ~~Add support for removing items by range (i.e. `~items[1:4]` would remove items at indices 1, 2, 3 and 4).~~ ✅
* Add support for removing custom items by condition (i.e., `~people={age < 16}` would remove from the people collection all objects with the age key-value pair with age less than 16).
* ~~Add support for datetime expressions in JSON.~~ ✅