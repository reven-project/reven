from __future__ import annotations
from collections.abc import Iterable
from enum import Enum
import importlib
import io
import os
import pkgutil
from typing import (
    Annotated,
    Any,
    Callable,
    Optional,
    Protocol,
    Self,
    TextIO,
    BinaryIO,
    Literal,
    Type,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)
import unittest
import cattr
import typer
import yaml
from rich.table import Table
from rich import print
from rich.markup import escape
from dataclass_wizard import YAMLWizard


class InputFormat(str, Enum):
    FILE_LIST = "file_list"
    YAML = "yaml"


class YAML(YAMLWizard):
    def __init_subclass__(cls):
        super().__init_subclass__(key_transform="NONE")


class TabularColumn:
    def __init__(
        self,
        name: Optional[str] = None,
        serialize: bool = False,
        hidden: bool = False,
        format: Optional[Callable[[Tabular, Any], str]] = None,
        highlight: Optional[Callable[[Tabular, Any], Optional[str]]] = None,
    ):
        self.name = name
        self.serialize = serialize
        self.hidden = hidden
        self.format = format
        self.highlight = highlight


def _to_table[T: Tabular](cls: Type[T], obj: T):
    annotations = cls.__annotations__
    type_hints = get_type_hints(cls)

    # retrieve columns
    columns = dict()
    for key, typ in annotations.items():
        col = None
        if get_origin(typ) == Annotated:
            for arg in get_args(typ):
                if isinstance(arg, TabularColumn):
                    col = arg
        if col is None:
            col = TabularColumn()
        columns[key] = col

    # create table
    table = Table(
        *(
            col.name or key.replace("_", " ").title()
            for key, col in columns.items()
            if not col.hidden
        )
    )

    for item in obj:
        values = []
        for key, col in columns.items():
            if col.hidden:
                continue
            value = getattr(item, key)
            key_class = type_hints[key]
            key_class_origin = get_origin(key_class)
            key_class_args = get_args(key_class)

            if col.serialize:
                values.append(yaml.safe_dump(cattr.Converter().unstructure(value)))
            elif (
                key_class_origin is not None
                and len(key_class_args) > 0
                and issubclass(key_class_origin, Iterable)
                and issubclass(key_class_args[0], Tabular)
            ):
                values.append(_to_table(key_class_args[0], value))
            else:
                highlight = col.highlight(item, value) if col.highlight else None
                if col.format:
                    value = col.format(item, value)
                else:
                    value = str(value)
                value = escape(value)
                if highlight:
                    value = f"[{highlight}]{value}[/{highlight}]"
                values.append(value)
        table.add_row(*values)

    return table


@runtime_checkable
class Tabular(Protocol):
    @classmethod
    def tabular_write(cls: Type[Self], file: TextIO, obj: list[Self]):
        if len(obj) == 0:
            if not is_tty(file):
                yaml.safe_dump([], file)
            return

        annotations = cls.__annotations__

        # retrieve columns
        columns = dict()
        for key, type in annotations.items():
            col = None
            if get_origin(type) == Annotated:
                for arg in get_args(type):
                    if isinstance(arg, TabularColumn):
                        col = arg
            if col is None:
                col = TabularColumn()
            columns[key] = col

        # write columns to file
        if is_tty(file):
            print(_to_table(cls, obj), file=file)
        else:
            unstructured = cattr.Converter().unstructure(obj)
            yaml.safe_dump(unstructured, file)


def exec_command(
    f: Callable[[TextIO | BinaryIO], None],
    mode: Literal["text"] | Literal["binary"] = "text",
) -> str | bytes:
    if mode == "text":
        output = io.StringIO()
        f(output)
        output.seek(io.SEEK_SET, 0)
        return output.getvalue().strip()
    elif mode == "binary":
        output = io.BytesIO()
        f(output)
        return output.getvalue()
    else:
        raise Exception("invalid mode")


def is_tty(f: io.TextIOBase | io.RawIOBase | io.BufferedIOBase) -> bool:
    """Returns whether or not an IO object is a tty"""
    try:
        fd = f.fileno()
    except OSError:
        # no fd, not a tty
        return False
    return os.isatty(fd)


def load_plugin_apps() -> list[typer.Typer]:
    return {
        getattr(importlib.import_module(name), "app")
        for _, name, _ in pkgutil.iter_modules()
        if name.startswith("reven_plugin_")
    }


class Nibbles:
    def __init__(self, data: bytes):
        self.data = data

    def __iter__(self):
        return Nibbles.__NibblesIterator(self)

    def __len__(self) -> int:
        return len(self.data) * 2

    def __getitem__(self, index: int) -> int:
        (quot, rem) = (index // 2, index % 2)
        match rem:
            case 0:
                return (self.data[quot] & 0xF0) >> 4
            case 1:
                return self.data[quot] & 0xF

    def __contains__(self, value: int) -> bool:
        for i in self:
            if i == value:
                return True
        return False

    class __NibblesIterator:
        def __init__(self, nibbles: Nibbles):
            self.index = 0
            self.nibbles = nibbles

        def __iter__(self):
            return self

        def __next__(self):
            if self.index >= len(self.nibbles):
                raise StopIteration
            v = self.nibbles[self.index]
            self.index += 1
            return v


class NibblesTests(unittest.TestCase):
    def test_len(self):
        nibbles = Nibbles(b"\xde\xad")
        self.assertEqual(len(nibbles), 4)

    def test_iter(self):
        nibbles = Nibbles(b"\xde\xad")
        self.assertEqual(list(nibbles), [0xD, 0xE, 0xA, 0xD])

    def test_getitem(self):
        nibbles = Nibbles(b"\xde\xad")
        self.assertEqual(nibbles[0], 0xD)
        self.assertEqual(nibbles[1], 0xE)

    def test_contains(self):
        nibbles = Nibbles(b"\xde\xad")
        self.assertFalse(0xC in nibbles)
        self.assertTrue(0xA in nibbles)
