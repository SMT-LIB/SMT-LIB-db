/* 
 * This file is a nix expression which can be used to get an isolated
 * development environemt.
 *
 * When the nix package manager is installed run 
 *  > nix-shell
 * to get a shell with the dependenies of schedgen present. This was only tested
 * on NixOS, but should work on other platforms which are supported by the Nix
 * packagemanger (such as MacOS X) too.
 */

{ pkgs ? import <nixpkgs> {} }:
with import <nixpkgs> {};
let
  matplot2tikz = python312.pkgs.buildPythonPackage {
    pname = "matplot2tikz";
    version = "0.4.1";
    doCheck = false;
    format = "pyproject";
    nativeBuildInputs = with pkgs.python312Packages; [ setuptools setuptools-scm wheel matplotlib numpy pillow webcolors ];
    propagatedBuildInputs = with pkgs.python312Packages; [ setuptools setuptools-scm ];
    preBuild = ''
      cat > pyproject.toml << EOF
[build-system]
requires = ["setuptools>=68", "setuptools_scm[toml]>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "matplot2tikz"
description = "Convert matplotlib figures into TikZ/PGFPlots"
readme = "README.md"
keywords = ["latex", "tikz", "matplotlib", "graphics"]
dynamic = ["version"]
requires-python = ">=3.9"
dependencies = [
  "matplotlib >= 1.4.0",
  "numpy",
  "Pillow",
  "webcolors",
  "typing_extensions >= 4.5",
]
authors = [
    {name="Erwin de Gelder", email="erwindegelder@gmail.com"},
    {name="Nico Schlömer", email="nico.schloemer@gmail.com"},
]
classifiers=[
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

# Enables the usage of setuptools_scm
[tool.setuptools_scm]

[project.optional-dependencies]
lint = [
    "mypy",
    "ruff",
]
test = [
    "pytest>=7.4.1",
    "pytest-cov>=6.0.0",
    "coverage[toml]>=7.0.0",
    "typeguard>=4.4.0",
]
dev = [
    "tox",
    "tox-pyenv-redux",
    "mypy",
    "ruff",
    "pytest>=7.4.1",
    "pytest-cov>=6.0.0",
    "coverage[toml]>=7.0.0",
    "typeguard>=4.4.0",
]

[tool.ruff]
line-length = 100
src = ["src"]
extend-exclude = [
    "conf.py",
]
target-version = "py39"
lint.select = ["ALL"]
lint.ignore = [
    "COM812",   # Conflicts with the formatter
    "ISC001",   # Conflicts with the formatter
    "PT001",    # https://github.com/astral-sh/ruff/issues/8796#issuecomment-1825907715
    "PT023",    # https://github.com/astral-sh/ruff/issues/8796#issuecomment-1825907715
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = [
    "S101", # Use of `assert` detected
    "D103", # Missing docstring in public function
]
"**/__init__.py" = [
    "F401", # Imported but unused
]
"docs/**" = [
    "INP001",   # Requires __init__.py but docs folder is not a package.
]

[tool.ruff.lint.pyupgrade]
# Preserve types, even if a file imports `from __future__ import annotations`(https://github.com/astral-sh/ruff/issues/5434)
keep-runtime-typing = true

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.mypy]
disallow_untyped_defs = true # Functions need to be annotated
warn_unused_ignores = true
exclude = [
    "matplot2tikz-\\\\d+", # Ignore temporary folder created by setuptools when building an sdist
    "venv.*/",
    "build/",
    "dist/",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
addopts = """
    --import-mode=append
    --cov=matplot2tikz
    --cov-config=pyproject.toml
    --cov-report=
    """

[tool.coverage.paths]
# Maps coverage measured in site-packages to source files in src
source = ["src/", ".tox/*/lib/python*/site-packages/"]

[tool.coverage.html]
directory = "reports/coverage_html"
    '';
    src = fetchPypi {
      pname = "matplot2tikz";
      version = "0.4.1";
      hash = "sha256-FZ41809D9QOKYBKBlgZWfGWsOxitHoXFryIxp2r7YBQ=";
    };
  };

in
pkgs.stdenv.mkDerivation {
  name = "SMT-LIB-db";

  hardeningDisable = [ "all" ];
  buildInputs = with pkgs; [
      python3
      sqlitebrowser
      sqlite
      zig_0_13
      zstd
      black
      parallel
      csvkit
      gmp
      python312Packages.beautifulsoup4
      python312Packages.flask
      python312Packages.gunicorn
      python312Packages.polars
      python312Packages.altair
      python312Packages.pip
      python312Packages.vega
      python312Packages.rich
      python312Packages.matplotlib
      python312Packages.numpy
      matplot2tikz
  ];

}
