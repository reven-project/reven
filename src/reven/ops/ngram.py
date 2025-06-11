import attr
import typer

from typing_extensions import Annotated
import sys
import reven.fast.ngram as fast_ngram
from reven.lib import is_tty, InputFormat, Tabular, TabularColumn
import yaml

app = typer.Typer()


@attr.s(auto_attribs=True)
class FileCount:
    file_name: str
    count: int


@attr.s(auto_attribs=True)
class Ngram(Tabular):
    ngram: Annotated[bytes, TabularColumn("N-Gram")]
    total_count: int
    file_counts: Annotated[
        list[FileCount],
        TabularColumn(
            "File Count(s)",
            format=lambda _, x: "\n".join(f"{y.file_name}: {y.count}" for y in x),
        ),
    ]


@app.command(help="Finds the n-grams for the files provided in stdin and arguments.")
def ngram(
    n: Annotated[int, typer.Argument(help="The number of bytes per n-gram.")] = 8,
    inputs: Annotated[
        list[typer.FileBinaryRead],
        typer.Argument(help="The files to find n-grams in."),
    ] = None,
    output: Annotated[typer.FileTextWrite, typer.Option("--output", "-o")] = sys.stdout,
    stdin_format: Annotated[
        InputFormat,
        typer.Option("--stdin-format", "-i", help="The format used to read stdin."),
    ] = InputFormat.FILE_LIST,
):
    inputs: set[typer.FileBinaryRead] = set(inputs) if inputs else set()

    if not is_tty(sys.stdin):
        match stdin_format:
            case InputFormat.FILE_LIST:
                files = sys.stdin.read().split()
            case InputFormat.YAML:
                files = (item["file_name"] for item in yaml.safe_load(sys.stdin))

        inputs.update(typer.FileBinaryRead(open(file, "rb")) for file in files)

    ngrams: dict[str, Ngram] = {}
    try:
        for file in inputs:
            data = file.read()

            counts: dict[str, int] = fast_ngram.count_ngrams(data, n)
            counts = dict(
                filter(lambda x: x[1] > 5, counts.items())
            )  # Filter to avoid storing every possible ngram.

            for ngram, count in counts.items():
                if ngram in ngrams:
                    ngrams[ngram].total_count += count
                    ngrams[ngram].file_counts.append(FileCount(file.name, count))
                else:
                    ngrams[ngram] = Ngram(
                        ngram.hex(), count, [FileCount(file.name, count)]
                    )

    except Exception as e:
        print(f"Failed to find ngrams: {e}", file=sys.stderr)
        raise exit(1)

    if output:
        Ngram.tabular_write(output, list(ngrams.values()))

    return ngrams
