#!/usr/bin/env python3

"""
Odd averange rating by age
"""


import argparse
import sqlite3
import matplotlib.pyplot as plt
import matplot2tikz
import numpy as np
from matplotlib.patches import Rectangle

parser = argparse.ArgumentParser()

parser.add_argument("database")
parser.add_argument("--logic", default="ALL")

args = parser.parse_args()

if args.logic == "ALL":
    args.logic = "%"

connection = sqlite3.connect(args.database)

years = list(range(2005, 2026))

query = connection.execute(
    """
    WITH benchmark_eval AS (
      SELECT
        r.rating AS eval_rating,
        CAST(MAX(0, (julianday(e.date) - julianday(f.firstOccurrence)) / 365.25) AS INT) AS age_year
      FROM Ratings r
      JOIN Evaluations e ON r.evaluation = e.id
      JOIN Queries q ON q.id = r.query
      JOIN Benchmarks b ON q.benchmark = b.id
      JOIN Families f ON f.id = b.family
    )
    SELECT
        age_year,
        AVG(eval_rating)
    FROM benchmark_eval
    GROUP BY age_year
    ORDER BY age_year DESC;
    """
)
results = query.fetchall()
for year, avg in results:
    print(f"{year} {avg:.2f}")

year, avg = zip(*results)

fig, ax = plt.subplots()
ax.plot(year, avg, "o-", linewidth=2)

ax.set_ylabel("Average Rating")
ax.set_xlabel("Age at Evaluation")
ax.set(xlim=(0, 20), xticks=range(0, 21))
ax.grid(True)

matplot2tikz.save("ratingage.tex")
plt.show()
