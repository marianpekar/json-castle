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
# python examples/example.py examples/example.json node.number=1 ~node.tags[0] node.next_node.number=2 +node.next_node.tags=foo ~node.next_node.tags=buzz
# and compare print in console with example.json to see the effect of environment local variable 
# substitutions and CLI overrides
cfg = JsonCastle.load_from_file(Cfg, sys.argv[1], **JsonCastle.parse_args(sys.argv, 2))
pprint(cfg)