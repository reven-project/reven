from dataclasses import dataclass
from sklearn.cluster import HDBSCAN
from typing_extensions import Annotated
import typer
import sys
import itertools
import unittest
import math
import reven.fast.pattern as pattern_fast
import functools
import io
from typing import Iterator, Union, Literal
from reven.lib import YAML, InputFormat, Nibbles, is_tty

app = typer.Typer()


class Pattern:
    def __init__(self, s: str):
        clean = s.replace(" ", "").lower()
        difference = set(clean).difference(set("0123456789abcdef?"))
        if len(difference) != 0:
            raise ValueError("invalid pattern characters")
        self.string = clean

    def print(self, output: typer.FileTextWrite, num_cols: int = 16):
        if not is_tty(output):
            print(self.string, file=output)
            return

        print(
            f"\x1b[1;37mAddress  \x1b[0;36m{' '.join(map(lambda x: hex(x)[2:].zfill(2), range(num_cols)))}\x1b[0m",
            file=output,
        )
        for address, nibbles in enumerate(itertools.batched(self.string, num_cols * 2)):
            pretty_nibbles = map(
                lambda x: "?" if x == "?" else f"\x1b[1;32m{x}\x1b[0m", nibbles
            )
            pretty_bytes = map(
                lambda x: "".join(x), itertools.batched(pretty_nibbles, 2)
            )

            print(
                f"\x1b[0;36m{hex(address * num_cols)[2:].zfill(8)}\x1b[0m {' '.join(pretty_bytes)}",
                file=output,
            )

    @functools.cached_property
    def bits(self) -> bytes:
        nibbles_high = (0x0 if x == "?" else int(x, base=16) for x in self.string[0::2])
        nibbles_low = (0x0 if x == "?" else int(x, base=16) for x in self.string[1::2])
        return bytes(
            (
                a << 4 | b
                for a, b in itertools.zip_longest(
                    nibbles_high,
                    nibbles_low,
                    fillvalue=0,
                )
            )
        )

    @functools.cached_property
    def mask(self) -> bytes:
        nibbles_mask_high = (0x0 if x == "?" else 0xF for x in self.string[0::2])
        nibbles_mask_low = (0x0 if x == "?" else 0xF for x in self.string[1::2])
        return bytes(
            (
                a << 4 | b
                for a, b in itertools.zip_longest(
                    nibbles_mask_high,
                    nibbles_mask_low,
                    fillvalue=0,
                )
            )
        )

    @property
    def bytelen(self) -> int:
        return math.ceil(len(self.string) / 2)

    def search(
        self, data: bytes, mode: Union[Literal["byte"], Literal["nibble"]] = "byte"
    ) -> list[int]:
        match mode:
            case "byte":
                step = 2
            case "nibble":
                step = 1
        return pattern_fast.pattern_search(self.string.encode("ascii"), data, step)

    def __str__(self):
        return self.string


def bytes_and(a: bytes, b: bytes) -> Iterator[int]:
    return (a & b for a, b in zip(a, b))


def find_pattern(bufs: list[Nibbles]) -> Pattern:
    pattern = ""
    for nibbles in zip(*bufs):
        if len(set(nibbles)) == 1:
            pattern += hex(nibbles[0])[2:]
        else:
            pattern += "?"

    return Pattern(pattern)


@dataclass
class PatternCluster(YAML):
    files: list[str]
    pattern: Pattern


@dataclass
class PatternClusters(YAML):
    clusters: list[PatternCluster]
    unclustered: PatternCluster | None


@app.command(
    help="Groups files based on similarity and finds patterns for these groups."
)
def find_patterns_grouped(
    length: int,
    inputs: list[typer.FileBinaryRead],
    start_offset: int = 0,
    output: typer.FileTextWrite | None = sys.stdout,
):
    nibs = []
    for input in inputs:
        input.seek(start_offset)
        nibs.append(Nibbles(input.read(length)))

    hdb = HDBSCAN()
    hdb.fit(nibs)
    labels = hdb.labels_
    clusters = dict()
    for cluster in set(labels):
        data = [
            (inputs[i], nibs[i]) for i, label in enumerate(labels) if label == cluster
        ]
        pattern = find_pattern([buf for _, buf in data])
        pattern_cluster = PatternCluster([input.name for input, _ in data], pattern)
        clusters[cluster] = pattern_cluster

    unclustered = clusters.get(-1)
    clusters.pop(-1, None)

    pattern_clusters = PatternClusters(
        clusters=[
            cluster for (_, cluster) in sorted(clusters.items(), key=lambda x: x[0])
        ],
        unclustered=unclustered,
    )

    if output:
        output.write(pattern_clusters.to_yaml())
    return pattern_clusters


@app.command(help="Find a common pattern for all the provided input files.")
def find_patterns(
    length: Annotated[int, typer.Argument()] = -1,
    inputs: Annotated[
        list[typer.FileBinaryRead],
        typer.Argument(
            help="Reads from stdin if not provided. Parsing depends on the --input-format option."
        ),
    ] = None,
    input_format: Annotated[
        InputFormat,
        typer.Option("--input-format", "-i"),
    ] = InputFormat.FILE_LIST,
    output: Annotated[typer.FileTextWrite, typer.Option("--output", "-o")] = sys.stdout,
    start_offset: Annotated[
        int,
        typer.Option("--start-offset", "-s"),
    ] = 0,
    output_width: Annotated[int, typer.Option("--output-width", "-w")] = 16,
):
    datas: list[bytes] = []

    inputs: set[typer.FileBinaryRead] = set(inputs) if inputs else set()

    if not is_tty(sys.stdin):
        match input_format:
            case InputFormat.FILE_LIST:
                inputs.update(
                    typer.FileBinaryRead(open(file, "rb"))
                    for file in sys.stdin.read().split()
                )
            case InputFormat.YAML:

                @dataclass
                class InputDTO(YAML):
                    data: bytes

                datas.extend(
                    [
                        dto.data[start_offset:]
                        for dto in InputDTO.from_yaml(sys.stdin.read())
                    ]
                )

    for input in inputs:
        input.seek(start_offset, io.SEEK_SET)
        datas.append(input.read(length))

    bufs = [Nibbles(data[:length] if length != -1 else data) for data in datas]

    find_pattern(bufs).print(output, output_width)


class PatternTests(unittest.TestCase):
    def test_search_ok(self):
        p = Pattern("01 01 ?? 01")
        results = p.search(b"\x01\x01\xfe\x01\x01\x01\x01")
        self.assertEqual([0, 3], results)

    def test_search_empty(self):
        p = Pattern("01 01 ?? 01")
        results = p.search(b"\x01\x20\x01\x01")
        self.assertEqual([], results)
