import sqlite3
import os
import polars as pl
import altair as alt
from flask import Flask, g, abort, render_template, request
from typing import *
from collections import defaultdict
from random import Random
import math


def init_routes(app, get_db):
    @app.route("/timeline/<string:logic_name>")
    def show_timeline(logic_name):
        connection = get_db().cursor()
        if logic_name == "ALL":
            logic_name = "%"

        years = list(range(2005, 2025))
        fresh = []
        used = []
        solved = []
        for year in years:
            yearstr = f"{year}-12-31"
            oldyearstr = f"{year-1}-12-31"
            # Counts benchark where there was a sat/unsat at some point before
            for row in connection.execute(
                """
                SELECT count(DISTINCT bnch.id) FROM Benchmarks AS bnch
                JOIN Queries AS qr  ON qr.benchmark = bnch.id
                JOIN Results AS res ON res.query = qr.id
                JOIN Evaluations as eval ON eval.id = res.evaluation
                WHERE NOT bnch.isIncremental
                AND eval.date <= ?
                AND (res.status == 'sat' OR res.status == 'unsat')
                AND bnch.logic LIKE ?;
                """,
                (oldyearstr, logic_name),
            ):
                this_solved = row[0]
                solved.append(this_solved)
            # Counts benchark that have a first occurence before the current year
            for row in connection.execute(
                """
                SELECT count(DISTINCT bnch.id) FROM Benchmarks AS bnch
                JOIN Queries AS  qr ON qr.benchmark = bnch.id
                JOIN Results AS res ON res.query = qr.id
                JOIN Evaluations AS eval ON eval.id = res.evaluation
                WHERE NOT bnch.isIncremental
                AND eval.date <= ?
                AND bnch.logic LIKE ?;
                """,
                (oldyearstr, logic_name),
            ):
                this_used = row[0]
                used.append(this_used - this_solved)
            # Counts fresh number of benchmarks
            for row in connection.execute(
                """
                SELECT COUNT(bnch.id) FROM Benchmarks AS bnch
                JOIN Families AS fam ON fam.id = bnch.family
                WHERE NOT bnch.isIncremental
                AND bnch.logic LIKE ?
                AND fam.firstOccurrence <= ?;
                """,
                (logic_name, yearstr),
            ):
                this_fresh = row[0]
                fresh.append(this_fresh - this_used)

        mydata = {"years": years, "solved": solved, "used": used, "fresh": fresh}
        pf = pl.DataFrame(mydata)
        chart = (
            alt.Chart(pf)
            .transform_fold(["fresh", "used", "solved"], as_=["type", "value"])
            .mark_area()
            .encode(x="years:T", y="value:Q", color="type:N")
            .properties(width=800, height=400)
        )
        charts = chart.to_html(fullhtml=False)

        # with alt.data_transformers.disable_max_rows():
        #     charts = g_select_provers.to_html(fullhtml=False)

        return render_template(
            "timeline.html",
            logicData=logic_name,
            printed=pf._repr_html_(),
            charts=charts,
        )
