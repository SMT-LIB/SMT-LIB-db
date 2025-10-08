import sqlite3
import os
import polars as pl
from pathlib import Path
from functools import cache
import polars_distance as pld
import altair as alt
from flask import Flask, g, abort, render_template, request
from typing import *
from collections import defaultdict
from random import Random
import math
import sklearn
import static_page.common_charts


def init_routes(app, get_db):
    @app.route("/charts/<string:logic_name>")
    def show_charts(logic_name):
        details_requested = request.args.get('details', default = False, type = bool)
        virtual_requested = request.args.get('virtual', default = False, type = bool)
        dist_too_few = request.args.get('dist_too_few', default = None, type = (lambda x: None if x == "" else float(x)))
        min_common_benches = request.args.get('min_common_benches', default = 100, type = int)
        
        r = static_page.common_charts.compute_charts(logic_name,details_requested,virtual_requested,dist_too_few,min_common_benches)

        return render_template(
            "isomap.html",
            logicData=logic_name,
            printed="",
            charts=r["all"].to_html(fullhtml=False),
            inputs_value=r,
        )
