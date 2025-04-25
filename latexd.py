#!/usr/bin/env python3


"""
latexd.py

A modular wrapper around `latexmk` to compile a LaTeX document using auxiliary files
from one or more separate directories (e.g., .sty, .bib, images).  The directory
containing the main .tex file is always automatically included, so local support
files live alongside your document without any extra flag.  All build artifacts
are kept in a temporary folder and cleaned up afterward.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import argparse
import platform
from collections import defaultdict


def parse_paths(path_string):
    """
    Parse a colon-separated path string and return a list of all filesystem directories.
    Handles recursive paths (with double slashes), environment variables, and home directory references.
    
    Args:
        path_string (str): A colon-separated path string like "/path/one//:/path/two:$HOME/path/three"
        
    Returns:
        list: List of all directory paths represented in the string
    """
    if not path_string:
        return []
    
    # Split by colon
    paths = path_string.split(':')
    
    # Remove empty entries that might come from trailing colons
    paths = [p for p in paths if p]
    
    result = []
    
    for path in paths:
        # Expand environment variables (like $HOME)
        expanded_path = os.path.expandvars(path)
        
        # Expand user directory references (like ~)
        expanded_path = os.path.expanduser(expanded_path)
        
        # Check if path has recursive marker (//)
        if '//' in expanded_path:
            # Split at the recursive marker
            base_path = expanded_path.split('//')[0]
            
            # Make sure base path exists before we try to walk it
            if os.path.isdir(base_path):
                # Walk directory recursively
                for root, dirs, _ in os.walk(base_path):
                    for directory in dirs:
                        result.append(os.path.join(root, directory))
                # Don't forget to include the base path itself
                result.append(Path(base_path).resolve())
        else:
            # Regular path (non-recursive)
            if os.path.isdir(expanded_path):
                result.append(Path(expanded_path).resolve())
    
    return result

def find_texdinputs():
    """
    Find the TEXDINPUTS environment variable and parse it into a list of directories.
    The format is similar to PATH, where directories are separated by colons.
    This function handles the recursive path marker (//) and expands environment variables.
    The directories are resolved to absolute paths and returned as a list.
    
    These directories are added to the extras directories for LaTeX compilation.
    If TEXDINPUTS is not set, an empty list is returned.

    Returns:
        list: List of directories in TEXDINPUTS.
    """
    texdinputs = os.getenv("TEXDINPUTS", "")
    if not texdinputs:
        return []
    
    # Parse the TEXDINPUTS variable
    return parse_paths(texdinputs)


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
            # don’t re‑import the main .tex (we already symlinked it above)
            if extra_file.name == tex_path.name:
                continue
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
    jobname = tex_filename.rsplit(".",1)[0] + "_build"
    cmd = [
        "latexmk",
        "-pdf",
        f"-jobname={jobname}",
        "-halt-on-error",
        "-interaction=nonstopmode",
        ] + latexmk_args + [tex_filename]
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
    output_pdf = build_dir / f"{tex_path.stem}_build.pdf"
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

    # If the filename ends with a trailing dot (e.g., "myfile."), remove the dot(s)
    if not tex_path.exists() and tex_path.name.endswith('.'):
        tex_path = tex_path.with_name(tex_path.name.rstrip('.'))

    # If the file doesn't exist and doesn't have a .tex extension, try appending .tex.
    if not tex_path.exists() and tex_path.suffix != ".tex":
        candidate = tex_path.with_suffix(".tex")
        if candidate.exists():
            tex_path = candidate
        else:
            tex_path = candidate

    if not tex_path.exists() or tex_path.suffix != ".tex":
        raise ValueError("Input must be a .tex file")

    extras_dirs = [Path(d).resolve() for d in extras_dirs or []]
    # make sure the .tex file’s own directory is also treated as an extras‐dir
    tex_dir = tex_path.parent.resolve()
    if tex_dir not in extras_dirs:
        extras_dirs.insert(0, tex_dir)
    latexmk_args = latexmk_args or []

    # Find TEXDINPUTS directories
    texdinputs_dirs = find_texdinputs()
    if texdinputs_dirs:
        for d in texdinputs_dirs:
            if d not in extras_dirs:
                extras_dirs.append(d)

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
        "-e", "--extras", 
        help="Directory with .bib/.sty/.cls files (can be used multiple times)",
        action="append",
        default=[]
    )
    parser.add_argument(
        "-c", "--copy-extras",
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
