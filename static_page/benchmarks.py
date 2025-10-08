#!/usr/bin/env python3

import sqlite3
import os
import argparse
import polars as pl
import altair as alt
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.progress import track


"""
    Writes HTML files for each benchmark.
"""

env = Environment(loader=PackageLoader("logics"), autoescape=select_autoescape())


def get_queries(cursor, benchmark_id):
    res = cursor.execute(
        """
           SELECT * FROM Queries WHERE benchmark=? 
           ORDER BY idx ASC
           LIMIT 101
           """,
        (benchmark_id,),
    )
    return res.fetchall()


def get_benchmark(cursor, benchmark_id):
    for row in cursor.execute(
        """
        SELECT b.id, b.name, logic, s.folderName, s.date, isIncremental, size,
               b.compressedSize, l.name, l.link, l.spdxIdentifier, generatedOn,
               generatedBy, generator, application, description, category,
               passesDolmen, passesDolmenStrict,
               queryCount, family, s.firstOccurrence,
               s.name AS familyName,
               l.name AS licenseName
               FROM Benchmarks AS b
                  INNER JOIN Families AS s ON s.Id = b.family
                  INNER JOIN Licenses AS l ON l.Id = b.license
        WHERE b.id=?""",
        (benchmark_id,),
    ):
        return row
    return None


def get_evaluations(cursor, query_id):
    res = cursor.execute(
        """
        SELECT ev.name, ev.date, ev.link, sol.name AS solverName,
               sovar.fullName, res.status, res.wallclockTime, res.cpuTime,
               rat.rating, rat.consideredSolvers, rat.successfulSolvers
        FROM Results AS res
        INNER JOIN Evaluations AS ev ON res.evaluation = ev.id
        INNER JOIN SolverVariants AS sovar ON res.solverVariant = sovar.id
        INNER JOIN Solvers AS sol ON sovar.solver = sol.id
        LEFT JOIN Ratings AS rat ON rat.evaluation = ev.id AND rat.query = res.query
        WHERE res.query = ?
        ORDER BY ev.date, sol.id, sovar.id
           """,
        (query_id,),
    )
    return res.fetchall()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("folder", help="output directory")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA cache_size = 10000;")

    benchmark_template = env.get_template("benchmark.html")

    res = connection.execute(
        """
            SELECT id FROM Benchmarks
        """
    )
    benchmarks = res.fetchall()
    benchmarks = list(map(lambda x: x[0], benchmarks))

    try:
        os.mkdir(f"{args.folder}/benchmarks")
    except:
        pass

    for benchmark_id in benchmarks:
        benchmark_data = get_benchmark(connection, benchmark_id)
        query_data = get_queries(connection, benchmark_id)
        evaluation = get_evaluations(connection, query_data[0]["id"])

        symbols = []
        for query in query_data:
            res = connection.execute(
                """
                SELECT s.name,sc.count FROM SymbolCounts AS sc
                INNER JOIN Symbols AS s ON s.id = sc.symbol
                WHERE sc.query=?""",
                (query["id"],),
            )
            symbols.append(res.fetchall())

        print(f"\tWriting benchmark {benchmark_id}")
        benchmark_template.stream(
            vega_version=alt.VEGA_VERSION,
            vegalite_version=alt.VEGALITE_VERSION,
            vegaembed_version=alt.VEGAEMBED_VERSION,
            benchmark=benchmark_data,
            evaluation=evaluation,
            queryData=list(zip(query_data, symbols)),
        ).dump(f"{args.folder}/benchmark/{benchmark_id}.html")
