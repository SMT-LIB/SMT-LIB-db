#!/usr/bin/env python3

import sqlite3
import os
import argparse
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.progress import track

"""
    Writes index.html and the overview of families and logics.
"""

env = Environment(
    loader=PackageLoader("families"),
    autoescape=select_autoescape()
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("folder", help="output folder")
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row

    logics_template = env.get_template("logics.html")
    family_template = env.get_template("family.html")

    res = connection.execute("""
            SELECT logic FROM Logics
        """)
    logics = res.fetchall()

    qf_logics = [l[0] for l in logics if l[0].startswith("QF_")]
    qf_logics.sort()
    quant_logics = [l[0] for l in logics if not l[0].startswith("QF_")]
    quant_logics.sort()

    logics = qf_logics + quant_logics

    logic_data = []
    for logic in logics:
        res = connection.execute("""
                SELECT fam.id, fam.name, fam.date FROM Families AS fam
                JOIN Benchmarks AS bench ON bench.family = fam.id
                WHERE bench.logic = ?
                GROUP BY fam.id;
            """, (logic,))
        families = res.fetchall()
        logic_data.append({"logic": logic, "families": families})

    try:
        os.mkdir(args.folder)
    except:
        pass
    logics_template.stream(logics=logic_data).dump(f"{args.folder}/index.html")

    res = connection.execute("SELECT * FROM Families;")
    families = res.fetchall()

    try:
        os.mkdir(f"{args.folder}/family")
    except:
        pass

    for fam in track(families, description="Generating families"):
        res = connection.execute("""
                SELECT bench.id, bench.logic, bench.name FROM Benchmarks AS bench
                WHERE bench.family = ?
                ORDER BY bench.logic;
            """, (fam['id'],))

        benchmarks = res.fetchall()
        family_template.stream(family=fam,benchmarks=benchmarks).dump(f"{args.folder}/family/{fam['id']}.html")
        
