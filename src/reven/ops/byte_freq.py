from typing import Annotated, Optional
import attr
import typer
import sys
from reven.lib import Tabular

app = typer.Typer()


@attr.s(auto_attribs=True, frozen=True)
class ByteFrequency(Tabular):
    value: int
    frequency: float


@attr.s(auto_attribs=True, frozen=True)
class FileFrequencies(Tabular):
    file_name: str
    frequencies: list[ByteFrequency]


@app.command(help="Calculates the byte frequencies of stdin or the given inputs.")
def byte_freq(
    inputs: Annotated[
        Optional[list[typer.FileBinaryRead]],
        typer.Argument(
            help="The input files to calculate byte frequencies for. Defaults to stdin."
        ),
    ] = None,
    output: typer.FileTextWrite = sys.stdout,
):
    if not inputs:
        inputs = [sys.stdin.buffer]

    freqs = []
    for input in inputs:
        data = input.read()
        freqs.append(
            FileFrequencies(
                file_name=input.name,
                frequencies=[
                    ByteFrequency(v, data.count(v) / len(data)) for v in range(0, 256)
                ],
            )
        )

    FileFrequencies.tabular_write(output, freqs)
