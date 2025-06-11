from typing import Optional
import attr
from typing_extensions import Annotated
import typer
import sys
from reven.ops.pattern import Pattern
from enum import Enum
from rich.progress import track
from rich.console import Console
from reven.lib import Tabular, TabularColumn, InputFormat, is_tty
import yaml


app = typer.Typer()


class StringFormat(str, Enum):
    TEXT = "text"
    HEX = "hex"
    PATTERN = "pattern"


@attr.s(auto_attribs=True, frozen=True)
class SearchDTO(Tabular):
    file_name: Annotated[
        str,
        TabularColumn(
            highlight=lambda self, _: "bold green" if self.matches else "bold red"
        ),
    ]
    count: int
    matches: Annotated[bool, TabularColumn(hidden=True)]
    positions: Annotated[
        list[int],
        TabularColumn(
            name="Addresses (Hex)", format=lambda _, x: " ".join(hex(y)[2:] for y in x)
        ),
    ]


def search_bytes(searchbytes: bytes, data: bytes) -> list[int]:
    index = -1
    indices = []
    while True:
        index = data.find(searchbytes, index + 1)
        if index == -1:
            break
        indices.append(index)
    return indices


def search_pattern(pattern: Pattern, data: bytes) -> list[int]:
    return list(pattern.search(data))


@app.command(help="Searches for data within inputs.")
def search(
    data_format: Annotated[
        StringFormat,
        typer.Option(
            help="The format of the data used in search.",
        ),
    ],
    data: Annotated[str, typer.Argument(help="The data to search for.")],
    inputs: Annotated[
        list[typer.FileBinaryRead],
        typer.Argument(help="The files to search within."),
    ] = None,
    input_format: Annotated[
        InputFormat,
        typer.Option(
            "--input-format", "-i", help="The format of input files in stdin."
        ),
    ] = InputFormat.FILE_LIST,
    output: Annotated[
        Optional[typer.FileTextWrite], typer.Option("--output", "-o")
    ] = sys.stdout,
    min_count: Annotated[
        int,
        typer.Option(
            "--min-count",
            "-m",
            help="Minimum number of occurrences to mark the file as matched.",
        ),
    ] = 1,
) -> list[SearchDTO]:
    match data_format:
        case StringFormat.TEXT:
            search_arg = data.encode("utf-8")
            search_fn = search_bytes
        case StringFormat.HEX:
            search_arg = bytearray.fromhex(data)
            search_fn = search_bytes
        case StringFormat.PATTERN:
            search_arg = Pattern(data)
            search_fn = search_pattern

    inputs: set[typer.FileBinaryRead] = set(inputs) if inputs else set()

    if not is_tty(sys.stdin):
        match input_format:
            case InputFormat.FILE_LIST:
                files = sys.stdin.read().split()
            case InputFormat.YAML:
                files = (item["file_name"] for item in yaml.safe_load(sys.stdin))

        inputs.update(typer.FileBinaryRead(open(file, "rb")) for file in files)

    dtos: list[SearchDTO] = []
    for input in track(inputs, console=Console(file=sys.stderr), description=""):
        data = input.read()
        indices = search_fn(search_arg, data)
        dtos.append(
            SearchDTO(
                file_name=input.name,
                matches=len(indices) >= min_count,
                count=len(indices),
                positions=indices,
            )
        )

    dtos = sorted(dtos, key=lambda x: x.file_name)

    if output:
        SearchDTO.tabular_write(output, dtos)

    return dtos
