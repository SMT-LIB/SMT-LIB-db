#!/usr/bin/env python3

import sqlite3
import os
import argparse
import polars as pl
import altair as alt
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.progress import track


"""
    Writes index.html and the overview of families and logics.
"""

env = Environment(loader=PackageLoader("logics"), autoescape=select_autoescape())

def bind_data(data, bins):
    hi = max(data)
    width = hi / bins
    counts = [0] * bins

    centers = [round(((i + 0.5) * width)/1024, 2) for i in range(bins)]

    for x in data:
        if x == hi:
            idx = bins - 1
        else:
            idx = int(x / width)
        counts[idx] += 1

    return counts, centers

if __name__ == "__main__":
    # alt.data_transformers.enable("vegafusion")

    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("folder", help="output directory")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA cache_size = 10000;")

    logic_template = env.get_template("logic.html")

    res = connection.execute(
        """
            SELECT logic FROM Logics
        """
    )
    logics = res.fetchall()
    logics.append(("ALL",))

    try:
        os.mkdir(f"{args.folder}/logics")
    except:
        pass

    for logic in logics:
        logic_print_name= logic[0]
        logic_name = logic_print_name
        if logic_print_name == "ALL":
            logic_name = "%"

        print(f"Generating {logic_print_name}")

        years = list(range(2005, 2025))
        fresh = []
        unsolved = []
        solved = []
        crafted = []
        industrial = []
        random = []
        for year in track(years):
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
                AND ((qr.status == 'unknown' OR (res.status == qr.status)))
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
                this_unsolved = row[0]
                unsolved.append(this_unsolved - this_solved)
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
                fresh.append(this_fresh - this_unsolved)

            for categoryRow in connection.execute(
                """
                SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
                JOIN Families AS fam ON fam.id = b.family
                WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
                """,
                (logic_name, "crafted", yearstr),
            ):
                crafted.append(categoryRow[0])
            for categoryRow in connection.execute(
                """
                SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
                JOIN Families AS fam ON fam.id = b.family
                WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
                """,
                (logic_name, "random", yearstr),
            ):
                random.append(categoryRow[0])
            for categoryRow in connection.execute(
                """
                SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
                JOIN Families AS fam ON fam.id = b.family
                WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
                """,
                (logic_name, "industrial", yearstr),
            ):
                industrial.append(categoryRow[0])

        res = connection.execute("""
                SELECT COUNT(bench.id) FROM Families AS fam
                JOIN Benchmarks AS bench ON bench.family = fam.id
                WHERE bench.logic LIKE ?
                GROUP BY fam.id;
            """, (logic_name,))
        family_sizes = res.fetchall()
        family_sizes = list(map(lambda x: x[0], family_sizes))

        res = connection.execute("""
                SELECT size, compressedSize FROM Benchmarks
                WHERE logic LIKE ?;
            """, (logic_name,))
        bench_sizes = res.fetchall()
        benchmark_sizes = list(map(lambda x: x['size'], bench_sizes))
        compressed_sizes = list(map(lambda x: x['compressedSize'], bench_sizes))

        res = connection.execute("SELECT id,name,date FROM Evaluations")
        evaluations = res.fetchall()
        solvers = []
        evalDates = []
        for evalId, evalName, evalDate in evaluations:
            for logicSolversRow in connection.execute(
                """
                SELECT COUNT(DISTINCT s.id) FROM Solvers AS s
                    INNER JOIN SolverVariants AS sv ON sv.solver = s.id
                    INNER JOIN Results AS r ON sv.id = r.solverVariant
                    INNER JOIN Benchmarks AS b ON b.id = r.query
                WHERE b.logic LIKE ? AND r.evaluation=? AND b.isIncremental=0
                """,
                (logic_name, evalId),
            ):
                solvers.append(logicSolversRow[0])
                evalDates.append(evalDate)

        mydata = {
            "years": years,
            "fresh": fresh,
            "unsolved": unsolved,
            "solved": solved,
        }
        pf = pl.DataFrame(mydata)
        timelinechart = (
            alt.Chart(pf)
            .transform_fold(["fresh", "unsolved", "solved"], as_=["type", "value"])
            .transform_calculate(
                order="{'fresh': 0, 'unsolved': 1, 'solved': 2}[datum.variable]"
            )
            .mark_area()
            .encode(
                x="years:O",
                y="value:Q",
                color=alt.Color("type:N", legend=alt.Legend(title='Freshness'))
                )
            .properties(width=800, height=300)
        )

        catdata = {
            "years": years,
            "industrial": industrial,
            "crafted": crafted,
            "random": random,
        }
        pf2 = pl.DataFrame(catdata)
        catchart = (
            alt.Chart(pf2)
            .transform_fold(["industrial", "crafted", "random"], as_=["type", "value"])
            .mark_area()
            .encode(
                x=alt.X("years:O", title="Years"),
                y=alt.Y("value:Q", title="Percentage of Benchmarks").stack("normalize"),
                color=alt.Color("type:N", 
                legend=alt.Legend(title='Category'))
            )
            .properties(width=800, height=300)
        )

        famsizedata = {"value": family_sizes}
        pf3 = pl.DataFrame(famsizedata)
        histochart = (
            alt.Chart(pf3).mark_bar().encode(
                x=alt.X("value:Q", bin=True, title="Family Size"),
                y=alt.Y('count()', title="Families"),
            )
            .properties(width=800, height=300)
        )

        (sizes_hist, centers) = bind_data(benchmark_sizes, 30)
        (compressed_hist, compressed_centers) = bind_data(compressed_sizes, 30)
        size_hist_data = {
            "histo": sizes_hist,
            "centers": centers,
        }
        compressed_hist_data = {
            "histo": compressed_hist,
            "centers": compressed_centers,
        }
        pf_size = pl.DataFrame(size_hist_data)
        pf_compressed = pl.DataFrame(compressed_hist_data)
        size_chart = (
            alt.Chart(pf_size, title="Benchmark Size")
            .transform_fold(["histo"], as_=["bucket", "size"])
            .mark_bar().encode(
                x=alt.X("centers:N", title="Size in Kibibytes"),
                y=alt.Y("size:Q", title="Benchmarks") #.scale(type="log")
            )
            .properties(width=800, height=300)
        )
        compressed_chart = (
            alt.Chart(pf_compressed, title="Compressed Benchmark Size")
            .transform_fold(["histo"], as_=["bucket", "size"])
            .mark_bar().encode(
                x=alt.X("centers:N", title="Size in Kibibytes"),
                y=alt.Y("size:Q", title="Benchmarks") #.scale(type="log")
            )
            .properties(width=800, height=300)
        )
        size_histo = size_chart & compressed_chart

        # benchmark_sizes_data = {"Raw": benchmark_sizes, "Compressed": compressed_sizes}
        # benchmark_sizes_pf = pl.DataFrame(benchmark_sizes_data)
        # size_histogram = alt.Chart(benchmark_sizes_pf).transform_fold(
        #         ['Raw', 'Compressed'],
        #         as_=['Size', 'Bytes']
        # ).mark_bar(
        #     opacity=0.3,
        #     binSpacing=0
        # ).encode(
        #     alt.X('Bytes:Q').bin(maxbins=100),
        #     alt.Y('count()').stack(None),
        #     alt.Color('Size:N')
        # ).properties(width=800, height=300)

        solverdata = {
            "years": evalDates,
            "solvers": solvers,
        }
        pf4 = pl.DataFrame(solverdata)
        solverchart = (
            alt.Chart(pf4)
            .transform_fold(["solvers"], as_=["type", "value"])
            .encode(
                x=alt.X("years:T", title="Competition Date"),
                y=alt.Y("value:Q", title="Number of Solvers")
            )
            .properties(width=800, height=300)
        )
        solverchart = solverchart.mark_line() + solverchart.mark_point()

        print(f"\tWriting {logic_print_name}.html")
        logic_template.stream(
            vega_version=alt.VEGA_VERSION,
            vegalite_version=alt.VEGALITE_VERSION,
            vegaembed_version=alt.VEGAEMBED_VERSION,
            logic=logic_print_name,
            tl_chart=timelinechart.to_json(indent=None),
            cat_chart=catchart.to_json(indent=None),
            fam_chart=histochart.to_json(indent=None),
            solvers_chart=solverchart.to_json(indent=None),
            size_chart=size_histo.to_json(indent=None)
            ).dump(
            f"{args.folder}/logics/{logic_print_name}.html"
        )
