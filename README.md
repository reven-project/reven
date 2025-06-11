# Reven 🦊

Reven is a flexible reverse engineering CLI toolkit written in Python and C. It is designed to facilitate the analysis of a large file set such as firmware files.

## Features ✨

- **Pipable**: The tool allows for piping of input and output in a queryable YAML format.
- **Tabular (powered by [Rich](https://github.com/Textualize/rich))**: The tool outputs pretty printed tables when its not piped.
- **Extendable**: Reven supports plugins, allowing users to extend its functionality and add custom features.

## Installation 👷

`reven` can be installed using `pip`.

```console
$ pip install reven
```

## Usage 🧑‍💻

Run `reven --help` to see the help and all available commands.

```console
$ reven --help

 Usage: reven [OPTIONS] COMMAND [ARGS]...

 Operations for reverse engineering sets of files.

╭─ Options ──────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.        │
│ --show-completion             Show completion for the current shell, to copy   │
│                               it or customize the installation.                │
│ --help                        Show this message and exit.                      │
╰────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────╮
│ search                  Searches for data within inputs.                       │
│ transform               Transforms an input to an output (e.g reverse).        │
│ byte-frequencies        Calculates the byte frequencies of the given inputs.   │
│ find-patterns-grouped   Groups files based on similarity and finds patterns    │
│                         for these groups.                                      │
│ find-patterns           Find a common pattern for all the provided input       │
│                         files.                                                 │
│ upset                   Creates an upset plot showing existential relations    │
│                         between data across files.                             │
│ slice                   Slice a file at start and end positions                │
│ hex2bin                 Command for converting Intel HEX files to binary       │
│                         files.                                                 │
│ ngram                   Finds the n-grams for the files provided in stdin and  │
│                         arguments.                                             │
│ etube                   Operations for reverse engineering Shimano E-Tube      │
│                         firmware                                               │
╰────────────────────────────────────────────────────────────────────────────────╯
```
