import typer

from reven.lib import load_plugin_apps

from . import search
from . import transform
from . import byte_freq
from . import pattern
from . import upset
from . import slice
from . import hex2bin
from . import ngram

app = typer.Typer(
    help="Operations for reverse engineering sets of files such as firmware and other binaries."
)

app.add_typer(search.app)
app.add_typer(transform.app)
app.add_typer(byte_freq.app)
app.add_typer(pattern.app)
app.add_typer(upset.app)
app.add_typer(slice.app)
app.add_typer(hex2bin.app)
app.add_typer(ngram.app)

for plugin_app in load_plugin_apps():
    app.add_typer(plugin_app)
