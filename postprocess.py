#!/usr/bin/env python3

import sqlite3
import argparse
import sys
from pathlib import Path
from modules import benchmarks, evaluations

parser = argparse.ArgumentParser(
    prog="populate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
parser.add_argument("SMTCOMPWEB_FOLDER", type=Path)
parser.add_argument("SMTCOMP_FOLDER", type=Path)
parser.add_argument("SMTEVAL_CSV", type=Path)
parser.add_argument("SMTEXEC_DB", type=Path)
parser.add_argument("SMTCOMP_RAW", type=Path)
parser.add_argument("STAREXEC_INC", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

benchmarks.calculate_benchmark_count(connection)
evaluations.add_smt_comps(
    connection,
    args.SMTCOMPWEB_FOLDER,
    args.SMTCOMP_FOLDER,
    args.SMTEVAL_CSV,
    args.SMTEXEC_DB,
    args.SMTCOMP_RAW,
    args.STAREXEC_INC,
)

print("Removing duplicates.")
connection.execute(
    "create index duplicateIdx on Results(query, solverVariant, status, evaluation);"
)
connection.execute(
    """
    DELETE FROM Results WHERE id > (
        SELECT MIN(id)
        FROM Results r2
        WHERE Results.evaluation = r2.evaluation
        AND Results.query = r2.query
        AND Results.solverVariant = r2.solverVariant
        AND Results.cpuTime = r2.cpuTime
        AND Results.wallclockTime = r2.wallclockTime
        AND Results.status = r2.status
    );"""
)
connection.commit()

print("Added competitions. Creating index for summaries.")
connection.execute("create index evalIdx4 on SolverVariants(solver);")
connection.execute(
    "create index evalIdx5 on Results(query, solverVariant, status, evaluation);"
)
connection.execute("create index evalIdx6 on Evaluations(date);")
connection.execute("create index evalIdx7 on Benchmarks(logic, isIncremental);")
connection.execute("create index evalIdx8 on Results(evaluation, solverVariant);")
connection.execute("create index evalIdx9 on Queries(benchmark);")
connection.execute("create index evalIdx10 on Results(query, status, evaluation);")

print("Adding summaries.")
evaluations.add_eval_summaries(connection)

print("Deleting indices.")
# Drop the indices such that we get a compact version.
connection.execute("drop index duplicateIdx;")
connection.execute("drop index evalIdx4;")
connection.execute("drop index evalIdx5;")
connection.execute("drop index evalIdx6;")
connection.execute("drop index evalIdx7;")
connection.execute("drop index evalIdx8;")
connection.execute("drop index evalIdx9;")
connection.execute("drop index evalIdx10;")

connection.close()
