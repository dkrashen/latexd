#!/usr/bin/env python3


"""
latexd.py

A modular wrapper around `latexmk` to compile a LaTeX document using auxiliary files
from one or more separate directories, while keeping auxiliary build files in a temporary directory.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import argparse
import platform
from collections import defaultdict

def open_pdf(pdf_path):
    """
    Open a PDF file using the system's default viewer.
    """
    pdf_path = str(Path(pdf_path))
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", pdf_path])
    elif system == "Windows":
        os.startfile(pdf_path)
    else:  # Linux or others
        subprocess.run(["xdg-open", pdf_path])

def prepare_build_directory(tex_path, extras_dirs, copy_extras):
    """
    Create and populate a temporary build directory.

    This function creates a temporary directory, symlinks (or copies) the main .tex file
    and any extra files from the provided directories into it.
    
    Parameters:
        tex_path (Path): The path to the main .tex file.
        extras_dirs (list[Path]): List of directories containing extra files (.sty, .bib, etc.).
        copy_extras (bool): Whether to copy extra files instead of symlinking.
    
    Returns:
        Path: The temporary build directory.
    """
    tmpdir = Path(tempfile.mkdtemp())
    filenames_seen = defaultdict(list)

    # Symlink the main .tex file
    tex_target = tmpdir / tex_path.name
    os.symlink(tex_path, tex_target)

    # Handle extras directories
    for extras_dir in extras_dirs:
        if not extras_dir.is_dir():
            print(f"Warning: extras path {extras_dir} is not a directory. Skipping.")
            continue
        for extra_file in extras_dir.glob("*"):
            dest = tmpdir / extra_file.name
            if dest.exists():
                filenames_seen[extra_file.name].append(str(extras_dir))
                continue
            if copy_extras:
                shutil.copy2(extra_file, dest)
            else:
                os.symlink(extra_file, dest)

    # Warn about duplicate filenames
    for filename, sources in filenames_seen.items():
        print(f"Warning: duplicate file '{filename}' found in multiple extras dirs:")
        for src in sources:
            print(f"  - {src}")

    return tmpdir

def compile_document(build_dir, tex_filename, latexmk_args, timeout=30):
    """
    Run latexmk in the specified build directory.

    Parameters:
        build_dir (Path): The temporary build directory.
        tex_filename (str): The filename of the .tex file in build_dir.
        latexmk_args (list): Additional command-line arguments for latexmk.
        timeout (int): Maximum time (in seconds) to wait for compilation.
    
    Returns:
        subprocess.CompletedProcess: The result of the compilation subprocess.
    """
    cmd = ["latexmk", "-pdf", "-halt-on-error", "-interaction=nonstopmode"] + latexmk_args + [tex_filename]
    try:
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        return result
    except subprocess.TimeoutExpired:
        print("LaTeX compilation timed out.")
        return None
    except subprocess.CalledProcessError as e:
        print("LaTeX compilation failed.")
        print("----- STDOUT -----")
        print(e.stdout)
        print("----- STDERR -----")
        print(e.stderr)
        return None

def post_process_pdf(build_dir, tex_path):
    """
    Copy the generated PDF from the build directory back to the original directory.

    Parameters:
        build_dir (Path): The temporary build directory.
        tex_path (Path): The original path to the .tex file.
    
    Returns:
        Path: The final location of the PDF, if generated.
    """
    output_pdf = build_dir / tex_path.with_suffix(".pdf").name
    final_output = tex_path.with_suffix(".pdf")
    if output_pdf.exists():
        shutil.copy2(output_pdf, final_output)
        return final_output
    else:
        print("PDF not generated.")
        return None

def run_latex_build(tex, extras_dirs=None, copy_extras=False, latexmk_args=None, preview=False):
    """
    Main function to compile a LaTeX document with optional extra directories.

    Parameters:
        tex (str): Path to the main .tex file.
        extras_dirs (list[str]): List of paths to directories with extra files.
        copy_extras (bool): Whether to copy extra files instead of symlinking.
        latexmk_args (list): Additional command-line arguments for latexmk.
        preview (bool): Whether to open the resulting PDF in the system viewer.
    """
    tex_path = Path(tex).resolve()
    if not tex_path.exists() or tex_path.suffix != ".tex":
        raise ValueError("Input must be a .tex file")

    extras_dirs = [Path(d).resolve() for d in extras_dirs or []]
    latexmk_args = latexmk_args or []

    # Prepare the build environment
    build_dir = prepare_build_directory(tex_path, extras_dirs, copy_extras)

    # Compile the document
    result = compile_document(build_dir, tex_path.name, latexmk_args)
    if result is None:
        return

    # Post-process the generated PDF
    final_pdf = post_process_pdf(build_dir, tex_path)
    if final_pdf:
        print("PDF successfully generated and copied to:", final_pdf)
        if preview:
            open_pdf(final_pdf)
    else:
        print("PDF generation failed.")

    # Clean up build directory
    shutil.rmtree(build_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compile LaTeX with external support files in a temporary directory."
    )
    parser.add_argument("tex", help="Path to main .tex file")
    parser.add_argument(
        "--extras",
        help="Directory with .bib/.sty/.cls files (can be used multiple times)",
        action="append",
        default=[]
    )
    parser.add_argument(
        "--copy-extras",
        help="Copy extra files instead of symlinking",
        action="store_true"
    )
    parser.add_argument(
        "-pv", "--preview",
        help="Open resulting PDF in default viewer",
        action="store_true"
    )
    # Parse known arguments; remaining ones are for latexmk.
    args, remaining = parser.parse_known_args()

    run_latex_build(
        tex=args.tex,
        extras_dirs=args.extras,
        copy_extras=args.copy_extras,
        latexmk_args=remaining,
        preview=args.preview
    )