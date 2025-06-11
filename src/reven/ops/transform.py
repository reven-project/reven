import typer
import sys
from enum import Enum

app = typer.Typer()


class Mode(str, Enum):
    REVERSE = "reverse"


@app.command(help="Transforms an input to an output (e.g reverse).")
def transform(
    mode: Mode,
    input: typer.FileText = sys.stdin,
    output: typer.FileTextWrite = sys.stdout,
):
    if mode is Mode.REVERSE:
        output.buffer.write(bytes(reversed(input.buffer.read())))
    else:
        raise Exception("unknown mode")
