#!/usr/bin/env python3

import argparse
import sqlite3
import statistics

""" Lists benchmarks that have gotten wrong answers in the past.
    What are does?
        in one year all results were the same answer,
        but different from the inferred status
"""


parser = argparse.ArgumentParser()

parser.add_argument("database")

args = parser.parse_args()

connection = sqlite3.connect(args.database)

# Get age of completely unsovled benchmarks
res = connection.execute(
    """
      SELECT bench.id, fam.folderName, bench.logic, bench.name FROM Results AS res1
      JOIN Queries AS sub      ON sub.id == res1.query
      JOIN Benchmarks AS bench ON sub.benchmark == bench.id
      JOIN Families AS fam     ON bench.family == fam.id
      WHERE (res1.status == "sat" OR res1.status == "unsat")
        AND (sub.inferredStatus == "sat" OR sub.inferredStatus == "unsat")
        AND res1.status != sub.inferredStatus
        AND NOT EXISTS (
                SELECT NULL
                FROM Results AS res2
                WHERE res1.query == res2.query
                  AND (res1.evaluation == res2.evaluation)
                  AND ((NOT res1.status == "unsat") OR res2.status == "sat")
                  AND ((NOT res1.status == "sat"  ) OR res2.status == "unsat")
            )
    GROUP BY bench.id;
    """
)
benchmarks = res.fetchall()

for bench in benchmarks:
    print(f"{bench[0]};{bench[2]};{bench[1]};{bench[3]}")
