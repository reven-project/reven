from pathlib import Path
import typer
import tempfile
import sys
import subprocess

app = typer.Typer()


@app.command(help="Command for converting Intel HEX files to binary files.")
def hex2bin(
    input: list[typer.FileText],
    output: typer.FileBinaryWrite = sys.stdout.buffer,
    output_dir: Path = None,
):
    outputs = [output]
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = [
            open(
                output_dir.joinpath(file.name.split("/")[-1].replace(".hex", ".bin")),
                "wb",
            )
            for file in input
        ]

    for file_in, file_out in zip(input, outputs):
        # Nordic nRF uses Intel HEX https://en.wikipedia.org/wiki/Intel_HEX
        with (
            tempfile.NamedTemporaryFile(delete_on_close=False) as fin,
            tempfile.NamedTemporaryFile(delete_on_close=False) as fout,
        ):
            fin.write(file_in.buffer.read())
            fin.close()
            fout.close()
            proc = subprocess.run(
                [
                    "objcopy",
                    "--input-target",
                    "ihex",
                    "--output-target",
                    "binary",
                    fin.name,
                    fout.name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if proc.returncode != 0:
                raise Exception(f"{proc.stdout.decode('utf-8').strip()}")

            with open(fout.name, "rb") as f:
                file_out.write(f.read())
                file_out.close()
