from dataclasses import dataclass
import io
import sys

from typing_extensions import Annotated
import typer
from reven.lib import YAML, InputFormat, is_tty

app = typer.Typer()


@dataclass
class SliceResult(YAML):
    file_name: str
    length: int
    data: bytes


@dataclass
class NumWithSign:
    sign: int
    num: int


def parse_num(s: str):
    return int(s, 0)


def parse_num_with_sign(s: str):
    sign = 0
    if s.startswith("+"):
        sign = 1
        s = s[1:]
    elif s.startswith("-"):
        sign = -1
        s = s[1:]
    return NumWithSign(sign, int(s, 0))


@app.command(
    help="Slice a file at start and end positions",
    context_settings={"ignore_unknown_options": True},
)
def slice(
    start: Annotated[
        int,
        typer.Argument(
            parser=parse_num,
            help="The position at which to start slicing. Can be prefixed with 0x, 0b, etc.",
        ),
    ],
    end: Annotated[
        NumWithSign,
        typer.Argument(
            parser=parse_num_with_sign,
            help="The position to slice until. "
            "If prefixed with +, the position is an offset from the start."
            "If prefixed with -, the position is an offset from the end of the file.",
        ),
    ],
    inputs: Annotated[
        list[typer.FileBinaryRead],
        typer.Argument(help="The files to slice."),
    ] = None,
    input_format: Annotated[
        InputFormat,
        typer.Option(
            "--input-format", "-i", help="The format of the files to slice in stdin."
        ),
    ] = InputFormat.FILE_LIST,
    output: Annotated[typer.FileTextWrite, typer.Option("--output", "-o")] = sys.stdout,
):
    dtos: list[SliceResult] = []

    inputs: dict[str, tuple[typer.FileBinaryRead, int]] = (
        {input.name: (input, 0) for input in inputs} if inputs else dict()
    )

    if not is_tty(sys.stdin):
        match input_format:
            case InputFormat.FILE_LIST:
                piped_inputs = set(
                    (file_name, 0) for file_name in sys.stdin.read().split()
                )

            case InputFormat.YAML:

                @dataclass
                class Input(YAML):
                    file_name: str
                    position: int

                in_dtos: list[Input] = Input.from_yaml(sys.stdin.read())
                piped_inputs = set((dto.file_name, dto.position) for dto in in_dtos)

        inputs.update(
            {
                file: (typer.FileBinaryRead(open(file, "rb")), pos)
                for (file, pos) in piped_inputs
            }
        )

    for input, pos in inputs.values():
        input.seek(0, io.SEEK_END)
        input_len = input.tell()
        input.seek(pos + start, io.SEEK_SET)

        match end.sign:
            case 1:
                length = end.num
            case 0:
                length = max(end.num - input.tell(), 0)
            case -1:
                length = max(input_len - input.tell() - end.num, 0)

        dtos.append(
            SliceResult(
                file_name=input.name,
                length=length,
                data=input.read(length)[:length],
            )
        )

    dtos = sorted(dtos, key=lambda x: x.file_name)

    output.write(SliceResult.list_to_yaml(dtos))
