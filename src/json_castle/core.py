from dataclasses import is_dataclass, fields
import math
from typing import IO, get_origin, get_args, Union
from enum import Enum
import os
import re
import json

class JsonCastle:
    """Built on top of the native json module for deserialization from JSON to data classes 
    with additional support for nested objects with variables, environment variables, and 
    post-load overrides."""
    
    __VAR_PATTERN = re.compile(r"\$\{(\w+)\}")
    __ENV_VAR_PATTERN = re.compile(r"%(\w+)%")
    __INDEXER_PATTERN = re.compile(r"(\w+)\[(\d+)\]")
    __INDEXER_SLICE_PATTERN = re.compile(r"(\w+)\[(\d*):(\d*)\]")
    __EXPR_PATTERN = re.compile(r"\{\{(.*?)\}\}")
     
    @staticmethod
    def parse_args(argv, start_idx = 1):
        """Parses command line arguments and returns a dictionary that can be passed 
        as **kwargs to load_from_file and load methods."""
        dct = {}
        for arg in argv[start_idx:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                dct[k] = v
            else:
                dct[arg] = None
        return dct

    @staticmethod
    def load_from_file(cls, path: str, **kwargs):
        """Read a JSON file at path and returns an instance of cls. Optionally you can 
        pass **kwargs to post-load overrides."""
        with open(path, "r") as f:
            return JsonCastle.load(cls, f, **kwargs)
    
    @staticmethod
    def load(cls, stream: IO[str], **kwargs):
        """Parses a JSON stream and returns an instance of cls. Optionally you can 
        pass **kwargs to post-load overrides."""
        data = json.load(stream)
        data = JsonCastle.__substitute_variables(data)
        data = JsonCastle.__evaluate_python(data)

        for k, v in kwargs.items():
            if k.startswith("+"):
                JsonCastle.__add_item(data, k[1:].split("."), v)
            elif k.startswith("~"):
                if k[1] == '!':
                    JsonCastle.__remove_item(data, k[2:].split("."), v, remove_all=True)
                else:
                    JsonCastle.__remove_item(data, k[1:].split("."), v)
            else:
                JsonCastle.__apply_overrides(data, k.split("."), v)

        return JsonCastle.__instantiate_dataclass(cls, data)

    @staticmethod
    def __substitute_variables(node, vars=None):
        if vars is None:
            vars = {}

        if isinstance(node, dict):
            result = {}
            for k, v in node.items():
                if k.startswith("$"):
                    v = JsonCastle.__substitute_variables(v, vars)
                    vars[k[1:]] = v
                else:
                    result[k] = JsonCastle.__substitute_variables(v, vars)
            return result

        elif isinstance(node, list):
            return [JsonCastle.__substitute_variables(item, vars) for item in node]

        elif isinstance(node, str):
            if node.startswith("${") and node.endswith("}"):
                var_name = node[2:-1]
                return vars.get(var_name, node)

            def repl_var(match):
                var_name = match.group(1)
                return str(vars.get(var_name, match.group(0)))

            node = JsonCastle.__VAR_PATTERN.sub(repl_var, node)

            def repl_env(match):
                env_name = match.group(1)
                return os.environ.get(env_name, match.group(0))

            return JsonCastle.__ENV_VAR_PATTERN.sub(repl_env, node)

        else:
            return node
        
    @staticmethod
    def __evaluate_python(node): 
        if isinstance(node, dict):
            result = {}
            for k, v in node.items():
                result[k] = JsonCastle.__evaluate_python(v)
            return result
        
        if isinstance(node, list):
            return [JsonCastle.__evaluate_python(item) for item in node]
        
        elif isinstance(node, str):
            if node.startswith("{{") and node.endswith("}}"):
                expression = node[2:-2]
                return str(eval(expression))

            def repl_expr(match):
                expression = match.group(1)
                return str(eval(expression))

            return JsonCastle.__EXPR_PATTERN.sub(repl_expr, node)
        
        else:
            return node
        
    @staticmethod
    def __apply_overrides(items, path, value):
        for i, part in enumerate(path):
            match = JsonCastle.__INDEXER_PATTERN.fullmatch(part)

            if match:
                key, idx = match.group(1), int(match.group(2))

                if key not in items or not isinstance(items[key], list):
                    items[key] = []

                while len(items[key]) <= idx:
                    items[key].append({})

                if i == len(path) - 1:
                    items[key][idx] = JsonCastle.__cast(value)
                else:
                    items = items[key][idx]
            else:
                if i == len(path) - 1:
                    items[part] = JsonCastle.__cast(value)
                else:
                    if part not in items or not isinstance(items[part], dict):
                        items[part] = {}
                    items = items[part]

    @staticmethod
    def __add_item(items, path, new_item):
        for part in path[:-1]:
            if part not in items or not isinstance(items[part], dict):
                items[part] = {}
            items = items[part]

        last = path[-1]
        if last not in items or not isinstance(items[last], list):
            items[last] = []

        items[last].append(JsonCastle.__cast(new_item))

    @staticmethod
    def __cast(value):
        if not isinstance(value, str):
            return value

        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        for fn in (int, float):
            try:
                return fn(value)
            except ValueError:
                pass
        return value
            
    @staticmethod
    def __remove_item(items, path, value=None, remove_all=False):

        def is_number(s):
            try:
                float(s)
                return True
            except (ValueError, TypeError):
                return False

        def remove_item_by_range(match):
            key, start, end = match.groups()

            if key not in items or not isinstance(items[key], list):
                return

            start = int(start) if start else None
            end = int(end) if end else None

            if start is not None and end is not None:
                items[key] = items[key][:start] + items[key][end + 1:]
            elif start is not None:
                items[key] = items[key][:start]
            elif end is not None:
                items[key] = items[key][end + 1:]
            else:
                items[key] = []

        def remove_item_at_index(current, match, idx):
            key, index = match.group(1), int(match.group(2))

            if key not in current or not isinstance(current[key], list):
                return None, True

            if idx == len(path) - 1:
                if 0 <= index < len(current[key]):
                    current[key].pop(index)
                return current, True

            if 0 <= index < len(current[key]):
                return current[key][index], False
            return None, True

        def remove_item_by_value(current, part):
            target_list = current.get(part)
            if not isinstance(target_list, list):
                return

            normalized_value = value
            value_regex = None
            if is_number(value) and all(is_number(item) for item in target_list):
                normalized_value = float(value)
            else:
                value_regex = re.compile(value)

            new_items = []
            removed = False
            for item in target_list:
                if value_regex is not None:
                    is_found = bool(value_regex.fullmatch(item))
                else:
                    is_found = math.isclose(float(item), normalized_value)

                if is_found and (remove_all or not removed):
                    removed = True
                    continue

                new_items.append(item)

            current[part] = new_items

        for idx, part in enumerate(path):
            is_last = idx == len(path) - 1

            match = JsonCastle.__INDEXER_SLICE_PATTERN.match(part)
            if match:
                remove_item_by_range(match)
                return

            match = JsonCastle.__INDEXER_PATTERN.fullmatch(part)
            if match:
                items, stop = remove_item_at_index(items, match, idx)
                if items is None or stop:
                    return
                continue

            if is_last:
                if value is None:
                    items.pop(part, None)
                else:
                    remove_item_by_value(items, part)
                return

            if part not in items or not isinstance(items[part], dict):
                return
            items = items[part]

    @staticmethod
    def __instantiate_dataclass(cls, data):
        if not is_dataclass(cls) or data is None:
            import warnings
            warnings.warn(f"{cls} is not a data class. Returning data as is", UserWarning)
            return data

        kwargs = {}
        for f in fields(cls):
            field_value = data.get(f.name)
            field_type = f.type

            if field_value is None:
                kwargs[f.name] = None
                continue

            kwargs[f.name] = JsonCastle.__convert_value(field_type, field_value)

        return cls(**kwargs)

    @staticmethod
    def __convert_value(field_type, value):
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Union:
            for arg in args:
                if arg is type(None):
                    continue
                try:
                    return JsonCastle.__convert_value(arg, value)
                except Exception:
                    continue
            return value

        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return field_type(value)

        if origin is list:
            item_type = args[0] if args else object
            return [JsonCastle.__convert_value(item_type, v) for v in value]

        if origin is tuple:
            item_type = args[0] if args else object
            return tuple(JsonCastle.__convert_value(item_type, v) for v in value)

        if origin is dict:
            key_type, val_type = args if args else (object, object)
            return {JsonCastle.__convert_value(key_type, k): JsonCastle.__convert_value(val_type, v) for k, v in value.items()}

        if is_dataclass(field_type):
            return JsonCastle.__instantiate_dataclass(field_type, value)

        return value