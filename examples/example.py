from pprint import pprint
import sys

from json_castle import JsonCastle
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

# Run
# python example.py node.number=1 ~node.tags[0] node.next_node.number=2 +node.next_node.tags=foo ~node.next_node.tags=buzz
# and compare print in console with example.json to see the effect of environment local variable 
# substitutions and CLI overrides
cfg = JsonCastle.load_from_file(Cfg, "example.json", **JsonCastle.parse_args(sys.argv))
pprint(cfg)