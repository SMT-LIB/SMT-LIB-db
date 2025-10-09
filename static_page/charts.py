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

app = typer.Typer()

env = Environment(
    loader=PackageLoader("charts"),
    autoescape=select_autoescape()
)

@app.command()
def html(database:Path,folder:Path,logic:list[str]=[],details:bool=False,virtual:bool=False,par4:bool=False,dist_too_few:float|None=None,min_common_benches:int=100,html:bool=True,pdf:bool=False,png:bool=False):

    os.makedirs(f"{folder}/isomap",exist_ok=True)
    os.makedirs(f"{folder}/isomap/pdf",exist_ok=True)
    os.makedirs(f"{folder}/isomap/png",exist_ok=True)
    charts_template = env.get_template("isomap.html")
    
    if len(logic) == 0:
        logic = common_charts.list_logics(database)
    
    for l in track(logic):
        try:
            r = common_charts.compute_charts(l,details,virtual,dist_too_few,min_common_benches,par4,database)

            if html:
                charts_template.stream(
                    logicData=l,
                    printed="",
                    charts=r["all"].to_html(fullhtml=False),
                    show_form=False,
                    inputs_value=r,
                ).dump(str(folder / "isomap" / f"{l}.html"))
            
            if pdf:
                r["all"].save(fp=folder / "isomap" / "pdf" / f"{l}.pdf",format="pdf")
            if png:
                r["all"].save(fp=folder / "isomap" / "png" / f"{l}.png",format="png")
        except Exception as e:
            print (f"Error during conversion of {l}:",e)

if __name__ == "__main__":
    app()