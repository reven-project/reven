from typing import Optional
import warnings
import attr
import sys
from typing_extensions import Annotated
import typer
from rich import print
from upsetplot import UpSet, from_indicators
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from pandas import DataFrame, MultiIndex
from reven.ops.search import search, StringFormat
from reven.lib import Tabular, TabularColumn


app = typer.Typer()


@attr.s(auto_attribs=True, frozen=True)
class UpsetDTO(Tabular):
    sets: Annotated[list[str], TabularColumn(format=lambda _, x: " ".join(x))]
    file_names: Annotated[list[str], TabularColumn(format=lambda _, x: "\n".join(x))]


@app.command(
    help="Creates an upset plot showing existential relations between data across files.",
)
def upset(
    data_format: Annotated[
        StringFormat,
        typer.Option(
            help="Set the format of the data to search for. \
Following are some examples for the different formats: \
Normal string example: 'et' 'Profile 1'. \
Hex encoded bytes example: '00 01' '00 02' OR '0001' '0002'. \
Pattern example: '?? 01' '?? 02' OR '??01' '??02'."
        ),
    ],
    data_and_paths: Annotated[
        list[str],
        typer.Argument(
            help="Expected format: 'foo' 'bar' ... : 'path/a.dat' 'path/b.dat' ... . \
The element ':' serves as a divider, where strings on the left side are parsed as search points \
and strings on the right side are parsed as paths to files to search within. \
A minimum of 2 search strings is required for this operation."
        ),
    ],
    output: Annotated[
        Optional[typer.FileTextWrite], typer.Option("--output", "-o")
    ] = sys.stdout,
    min_count: Annotated[
        int,
        typer.Option(help="Set the minimum required number of occurences in a file."),
    ] = 1,
):
    divider_i = data_and_paths.index(":")
    search_strings = data_and_paths[:divider_i]

    if len(search_strings) < 2:
        print(
            "Need at least 2 search strings to run comparisons! \
If you want to search only one string, use the 'search' operation instead ;)."
        )
        raise typer.Abort()

    # -- Search for string combinations --
    def get_input_files():
        return [open(path, "rb") for path in data_and_paths[divider_i + 1 :]]

    search_results = {
        f"{i + 1}-{j + 1}": list(
            filter(
                lambda s: s.matches,
                search(
                    data_format=data_format,
                    data="".join(search_strings[i : j + 1]),
                    inputs=get_input_files(),
                    output=None,
                    min_count=min_count,
                ),
            ),
        )
        for i in range(len(search_strings))
        for j in range(i, len(search_strings))
    }

    # -- Group the search result --
    inputs = get_input_files()
    categories = sorted([range_id for range_id in search_results], reverse=True)
    file_names = [file.name for file in inputs]

    data: dict[str, list[bool]] = {
        range_id: [fw in map(lambda s: s.file_name, range_res) for fw in file_names]
        for range_id, range_res in search_results.items()
    }

    file_name_col = "file names"
    df = (
        DataFrame({file_name_col: file_names, **data})
        .sort_index(axis=1)
        .sort_values(categories)  # Ensure 2 levels of sorting (bool values, fw names)
    )

    df["diff"] = df.drop(columns=[file_name_col]).diff().ne(0).any(axis=1).cumsum()
    groups = [group.drop(columns="diff") for _, group in df.groupby("diff")]

    dtos = []
    for group in groups:
        ranges_only = group.drop(columns=[file_name_col])

        names = ranges_only.columns[ranges_only.any()].to_list()
        if not names:
            names = ["0-0"]
        file_names = group.get(file_name_col).to_list()

        dtos.append(UpsetDTO(sets=names, file_names=file_names))

    upset_data = from_indicators(categories, data=df).drop(df.columns, axis=1)

    if not isinstance(upset_data.index, MultiIndex):
        print(
            "Not enough matching strings to produce a diagram. \
Need matching(s) of at least 2 search strings."
        )
        raise typer.Exit()

    # -- Create upset plot from groups --
    upset = UpSet(
        upset_data,
        orientation="horizontal",
        sort_by="degree",
        sort_categories_by="input",
        show_counts=True,
    )

    colors = matplotlib.colormaps.get_cmap("gist_rainbow")(
        np.linspace(0, 1, len(categories))
    )

    for cat, color in zip(categories, colors):
        upset.style_categories(
            categories=cat,
            bar_facecolor=(color[0], color[1], color[2]),
            shading_facecolor=(color[0], color[1], color[2], 0.1),
        )

    _ = [f.close() for f in inputs]

    if output:
        UpsetDTO.tabular_write(output, dtos)

    # Ignore warnings from upset package considering the package is unmaintained.
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)

        upset.plot()

    plt.show()
