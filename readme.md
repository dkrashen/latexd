# Latexd

A modular wrapper around `latexmk` to compile a LaTeX document using auxiliary files
from one or more separate directories (e.g., .sty, .bib, images).  The directory
containing the main .tex file is always automatically included, so local support
files live alongside your document without any extra flag.  All build artifacts
are kept in a temporary folder and cleaned up afterward.

## Overview

Latexd is a Python script that simplifies the process of compiling LaTeX
documents when your project relies on auxiliary files located in different
directories. The script sets up a temporary build directory, manages file
linking or copying, and leverages `latexmk` for efficient document compilation.
Additionally, it provides a cross-platform method for automatically opening the
generated PDF file in your system's default viewer.

## Features

- **Modular Build System:** Keeps auxiliary files separate from build files by creating a temporary build directory.

- **Multi-Directory Support:** Handles auxiliary files from one or more directories.

## Requirements

- **Python:** Version 3.6 or later.
- **latexmk:** Must be installed and available in your system’s PATH.  
[latexmk package on CTAN](https://ctan.org/pkg/latexmk)
- **LaTeX Distribution:** Such as TeX Live or MiKTeX.

## Installation

1. **Clone the Repository:**  
Open your terminal and run:
```bash
git clone https://github.com/dkrashen/latexd.git
cd latexd
```

2. **Ensure Python is Installed:**
Verify that Python 3.6 or later is installed:
```bash
python3 --version
```

3. **Install latexmk:**
Ensure latexmk is installed and available in your PATH. Installation methods vary by operating system:

Ubuntu/Debian:
```bash
sudo apt-get install latexmk
```

macOS (using Homebrew):
```bash
brew install latexmk
```
Windows:
Typically included in major LaTeX distributions like MiKTeX or TeX Live.

## Usage

Run the script directly from the command line. For example:

```bash
python3 latexd.py -i path/to/main.tex -e path/to/auxiliary/dir1 path/to/auxiliary/dir2 --copy-extras
```
or 
```bash
python3 latexd.py main.tex -e path/to/auxiliary/dir1 path/to/auxiliary/dir2 --copy-extras
```
- -i or --input: Specifies the path to the main LaTeX file.
- -e or --extras: One or more directories containing auxiliary files.
- --copy-extras: (Optional) Copy auxiliary files instead of creating symlinks.

For more options, run:

```bash
python3 latexd.py --help
```

## Credits

This project was developed by Danny Krashen with technical guidance and strategic advice from ChatGPT.

License

latexd (c) 2025 by Daniel Krashen is licensed under Creative Commons Attribution-ShareAlike 4.0 International 

⸻

Happy LaTeXding!
