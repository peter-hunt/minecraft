from dataclasses import dataclass


@dataclass
class Block:
    id: str = 'minecraft:air'
    state: dict[str, bool | int | str] = {}
