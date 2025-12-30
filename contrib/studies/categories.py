#!/usr/bin/env python3

import argparse
import sqlite3
import statistics

"""
    Number of benchmarks per category (crafted, industrial, random) and logic.
"""


parser = argparse.ArgumentParser()

parser.add_argument("database")

args = parser.parse_args()

connection = sqlite3.connect(args.database)

years = list(range(2005, 2025))

res = connection.execute("SELECT DISTINCT logic FROM Benchmarks")
logics = res.fetchall()

categories = ["crafted", "industrial", "random"]

print("Logic;crafted;industrial;random")
for (logic,) in logics:
    print(f"{logic}", end="")
    for cat in categories:
        for categoryRow in connection.execute(
            """
            SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
            WHERE b.logic=? AND b.category=?
            """,
            (logic, cat),
        ):
            print(f";{categoryRow[0]}", end="")
    print("")
