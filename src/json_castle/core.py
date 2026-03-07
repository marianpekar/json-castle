from dataclasses import is_dataclass, fields
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
    __EXPR_PATTERN = re.compile(r"\{\{(.*?)\}\}")
     
    @staticmethod
    def parse_args(argv):
        """Parses command line arguments and returns a dictionary that can be passed 
        as **kwargs to load_from_file and load methods."""
        dct = {}
        for arg in argv[1:]:
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
        dct = json.load(stream)
        dct = JsonCastle.__substitute_variables(dct)
        dct = JsonCastle.__evaluate_python(dct)

        for k, v in kwargs.items():
            if k.startswith("+"):
                JsonCastle.__add_item(dct, k[1:].split("."), v)
            elif k.startswith("~"):
                JsonCastle.__remove_item(dct, k[1:].split("."), v)
            else:
                JsonCastle.__apply_overrides(dct, k.split("."), v)

        return JsonCastle.__from_dict(cls, dct)

    @staticmethod
    def __substitute_variables(dct, vars=None):
        if vars is None:
            vars = {}

        if isinstance(dct, dict):
            result = {}
            for k, v in dct.items():
                if k.startswith("$"):
                    v = JsonCastle.__substitute_variables(v, vars)
                    vars[k[1:]] = v
                else:
                    result[k] = JsonCastle.__substitute_variables(v, vars)
            return result

        elif isinstance(dct, list):
            return [JsonCastle.__substitute_variables(item, vars) for item in dct]

        elif isinstance(dct, str):
            if dct.startswith("${") and dct.endswith("}"):
                var_name = dct[2:-1]
                return vars.get(var_name, dct)

            def repl_var(match):
                var_name = match.group(1)
                return str(vars.get(var_name, match.group(0)))

            dct = JsonCastle.__VAR_PATTERN.sub(repl_var, dct)

            def repl_env(match):
                env_name = match.group(1)
                return os.environ.get(env_name, match.group(0))

            return JsonCastle.__ENV_VAR_PATTERN.sub(repl_env, dct)

        else:
            return dct
        
    @staticmethod
    def __evaluate_python(dct): 
        if isinstance(dct, dict):
            result = {}
            for k, v in dct.items():
                result[k] = JsonCastle.__evaluate_python(v)
            return result
        
        if isinstance(dct, list):
            return [JsonCastle.__evaluate_python(item) for item in dct]
        
        elif isinstance(dct, str):
            if dct.startswith("{{") and dct.endswith("}}"):
                expression = dct[2:-2]
                return str(eval(expression))

            def repl_expr(match):
                expression = match.group(1)
                return str(eval(expression))

            return JsonCastle.__EXPR_PATTERN.sub(repl_expr, dct)
        
        else:
            return dct
        
    @staticmethod
    def __apply_overrides(dct, path, value):
        current = dct

        for i, part in enumerate(path):
            match = JsonCastle.__INDEXER_PATTERN.fullmatch(part)

            if match:
                key, idx = match.group(1), int(match.group(2))

                if key not in current or not isinstance(current[key], list):
                    current[key] = []

                while len(current[key]) <= idx:
                    current[key].append({})

                if i == len(path) - 1:
                    current[key][idx] = JsonCastle.__cast(value)
                else:
                    current = current[key][idx]
            else:
                if i == len(path) - 1:
                    current[part] = JsonCastle.__cast(value)
                else:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]

    @staticmethod
    def __add_item(dct, path, new_item):
        current = dct

        for part in path[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]

        last = path[-1]
        if last not in current or not isinstance(current[last], list):
            current[last] = []

        current[last].append(JsonCastle.__cast(new_item))

    @staticmethod
    def __cast(value):
        if not isinstance(value, str):
            return value

        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
            
    @staticmethod
    def __remove_item(dct, path, value=None):
        current = dct

        for idx, part in enumerate(path):
            match = JsonCastle.__INDEXER_PATTERN.fullmatch(part)

            if match:
                key, index = match.group(1), int(match.group(2))

                if key not in current or not isinstance(current[key], list):
                    return

                if idx == len(path) - 1:
                    if 0 <= index < len(current[key]):
                        current[key].pop(index)
                    return
                else:
                    if 0 <= index < len(current[key]):
                        current = current[key][index]
                    else:
                        return           
            else:
                if idx == len(path) - 1:
                    if value is None:
                        current.pop(part, None)
                    else:
                        current[part].remove(value)
                    return
                else:
                    if part not in current or not isinstance(current[part], dict):
                        return
                    current = current[part]

    @staticmethod
    def __from_dict(cls, dct):
        if not is_dataclass(cls) or dct is None:
            return dct

        kwargs = {}
        for f in fields(cls):
            field_value = dct.get(f.name)
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
            return JsonCastle.__from_dict(field_type, value)

        return value