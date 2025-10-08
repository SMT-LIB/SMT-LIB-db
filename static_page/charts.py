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

app = typer.Typer()

env = Environment(
    loader=PackageLoader("charts"),
    autoescape=select_autoescape()
)

@app.command()
def html(database:Path,folder:Path,logic:str,details:bool=False,virtual:bool=False,dist_too_few:float|None=None,min_common_benches:int=100):

    r = common_charts.compute_charts(logic,details,virtual,dist_too_few,min_common_benches,database)

    try:
        os.mkdir(f"{folder}/isomap")
    except:
        pass
    charts_template = env.get_template("isomap.html")
    charts_template.stream(
        logicData=logic,
        printed="",
        charts=r["all"].to_html(fullhtml=False),
        inputs_value=r,
    ).dump(f"{folder}/isomap/{logic}.html")

if __name__ == "__main__":
    app()