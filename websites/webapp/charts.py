#!/usr/bin/env python3
import sqlite3
import os
import polars as pl
import altair as alt
from typing import *
from collections import defaultdict
from random import Random
import math
from jinja2 import Environment, PackageLoader, select_autoescape
import argparse
import common_charts
import typer
from pathlib import Path
from rich.progress import track
import vl_convert
import altair.utils._importers
import json

app = typer.Typer()

env = Environment(loader=PackageLoader("charts"), autoescape=select_autoescape())


@app.command()
def solver(
    database: Path,
    folder: Path,
    logic: list[str] = [],
    details: bool = False,
    virtual: bool = False,
    par4: bool = False,
    dist_too_few: float | None = None,
    min_common_benches: int = 100,
    isomap: bool = False,
    euclidean: bool = False,
    html: bool = True,
    pdf: bool = False,
    png: bool = False,
    vega: bool = False,
    data: bool = False,
    index: bool = True,
):

    os.makedirs(f"{folder}/isomap", exist_ok=True)
    os.makedirs(f"{folder}/isomap/pdf", exist_ok=True)
    os.makedirs(f"{folder}/isomap/png", exist_ok=True)
    os.makedirs(f"{folder}/isomap/vega", exist_ok=True)
    os.makedirs(f"{folder}/isomap/data", exist_ok=True)
    charts_template = env.get_template("isomap.html")
    error_template = env.get_template("isomap_error.html")

    if len(logic) == 0:
        logic = common_charts.list_logics(database)

    logic.sort()
    failed_logics = []
    ok_logics = []

    for l in track(logic):
        try:
            r = common_charts.compute_charts(
                l,
                details,
                virtual,
                dist_too_few,
                min_common_benches,
                par4,
                isomap,
                euclidean,
                database,
            )
        except Exception as e:
            print(f"Error during conversion of {l}:", e)
            failed_logics.append(l)
            error_template.stream(
                title=f"Error {l} Isomap",
                logic=l,
            ).dump(str(folder / "isomap" / f"{l}.html"))
            continue
        ok_logics.append(l)

        if html:
            charts_template.stream(
                title=f"{l} Isomap",
                logicData=l,
                printed="",
                charts=r["all"].to_html(fullhtml=False),
                show_form=False,
                inputs_value=r,
            ).dump(str(folder / "isomap" / f"{l}.html"))

        if pdf:
            r["all"].save(fp=folder / "isomap" / "pdf" / f"{l}.pdf", format="pdf")
        if png:
            r["all"].save(fp=folder / "isomap" / "png" / f"{l}.png", format="png")
        if vega:
            vega_spec = vl_convert.vegalite_to_vega(
                vl_spec=r["all"].to_dict(context={"pre_transform": False}),
                vl_version=altair.utils._importers.vl_version_for_vl_convert(),
            )
            (folder / "isomap" / "vega" / f"{l}.json").write_text(
                json.dumps(vega_spec, indent=2)
            )
        if data:
            vega_spec = vl_convert.vegalite_to_vega(
                vl_spec=r["all"].to_dict(context={"pre_transform": False}),
                vl_version=altair.utils._importers.vl_version_for_vl_convert(),
            )
            vega_spec = {
                "data": vega_spec["data"][2]["values"],
                "domain": vega_spec["scales"][2]["domain"],
            }
            (folder / "isomap" / "data" / f"{l}.json").write_text(
                json.dumps(vega_spec, indent=2)
            )

    if index:
        env.get_template("isomap_index.html").stream(
            title="Isomap Overview",
            logics=ok_logics,
            failed_logics=failed_logics,
            pdf=pdf,
            html=html,
            png=png,
        ).dump(str(folder / "isomap" / "index.html"))

@app.command()
def bench(
    database: Path,
    folder: Path,
    logic: list[str] = [],
    par4: bool = False,
    min_common_benches: int = 100,
    isomap: bool = False,
    euclidean: bool = False,
    html: bool = True,
    pdf: bool = False,
    png: bool = False,
    vega: bool = False,
    data: bool = False,
    index: bool = True,
):

    os.makedirs(f"{folder}/isomap_bench", exist_ok=True)
    os.makedirs(f"{folder}/isomap_bench/pdf", exist_ok=True)
    os.makedirs(f"{folder}/isomap_bench/png", exist_ok=True)
    os.makedirs(f"{folder}/isomap_bench/vega", exist_ok=True)
    os.makedirs(f"{folder}/isomap_bench/data", exist_ok=True)
    charts_template = env.get_template("isomap.html")
    error_template = env.get_template("isomap_error.html")

    if len(logic) == 0:
        logic = common_charts.list_logics(database)

    logic.sort()
    failed_logics = []
    ok_logics = []
    
    alt.data_transformers.disable_max_rows()

    for l in track(logic):
        try:
            print(l)
            r = common_charts.compute_benchmark_charts(
                l,
                min_common_benches,
                par4,
                isomap,
                euclidean,
                database,
            )
        except Exception as e:
            print(f"Error during conversion of {l}:", e)
            failed_logics.append(l)
            error_template.stream(
                title=f"Error {l} Isomap",
                logic=l,
            ).dump(str(folder / "isomap_bench" / f"{l}.html"))
            continue
        ok_logics.append(l)

        if html:
            charts_template.stream(
                title=f"{logic} Isomap",
                logicData=l,
                printed="",
                charts=r["all"].to_html(fullhtml=False),
                show_form=False,
                inputs_value=r,
            ).dump(str(folder / "isomap_bench" / f"{l}.html"))

        if pdf:
            r["all"].save(fp=folder / "isomap_bench" / "pdf" / f"{l}.pdf", format="pdf")
        if png:
            r["all"].save(fp=folder / "isomap_bench" / "png" / f"{l}.png", format="png")
        if vega:
            vega_spec = vl_convert.vegalite_to_vega(
                vl_spec=r["all"].to_dict(context={"pre_transform": False}),
                vl_version=altair.utils._importers.vl_version_for_vl_convert(),
            )
            (folder / "isomap_bench" / "vega" / f"{l}.json").write_text(
                json.dumps(vega_spec, indent=2)
            )
        if data:
            vega_spec = vl_convert.vegalite_to_vega(
                vl_spec=r["all"].to_dict(context={"pre_transform": False}),
                vl_version=altair.utils._importers.vl_version_for_vl_convert(),
            )
            vega_spec = {
                "data": vega_spec["data"][2]["values"],
                "domain": vega_spec["scales"][2]["domain"],
            }
            (folder / "isomap_bench" / "data" / f"{l}.json").write_text(
                json.dumps(vega_spec, indent=2)
            )

    if index:
        env.get_template("isomap_index.html").stream(
            title="Isomap Overview",
            logics=ok_logics,
            failed_logics=failed_logics,
            pdf=pdf,
            html=html,
            png=png,
        ).dump(str(folder / "isomap_bench" / "index.html"))

if __name__ == "__main__":
    app()
