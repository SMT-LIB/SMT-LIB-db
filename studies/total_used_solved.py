#!/usr/bin/env python3

"""
Prints for each year:
  * num. of total benchmarks
  * num. of benchmarks that have appeared in an earlier competition
  * num. of benchmarks where a solver in an earlier competition returned "sat" or "unsat"
  -> non-incremental only
"""


import argparse
import sqlite3
import matplotlib.pyplot as plt
import matplot2tikz
import numpy as np

parser = argparse.ArgumentParser()

parser.add_argument("database")
parser.add_argument("--logic", default="ALL")

args = parser.parse_args()

if args.logic == "ALL":
    args.logic = "%"

connection = sqlite3.connect(args.database)

years = list(range(2005, 2026))
fresh = []
unsolved = []
solved = []
crafted = []
industrial = []
random = []

print(f"Year; Solved; Unsolved; Fresh")
for year in years:
    yearstr = f"{year}-12-31"
    oldyearstr = f"{year-1}-12-31"
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
        (oldyearstr, args.logic),
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
        (oldyearstr, args.logic),
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
        (args.logic, yearstr),
    ):
        this_fresh = row[0]
        fresh.append(this_fresh - this_unsolved)
    for categoryRow in connection.execute(
        """
        SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
        JOIN Families AS fam ON fam.id = b.family
        WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
        AND NOT b.isIncremental
        """,
        (args.logic, "crafted", yearstr),
    ):
        crafted.append(categoryRow[0])
    for categoryRow in connection.execute(
        """
        SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
        JOIN Families AS fam ON fam.id = b.family
        WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
        AND NOT b.isIncremental
        """,
        (args.logic, "random", yearstr),
    ):
        random.append(categoryRow[0])
    for categoryRow in connection.execute(
        """
        SELECT COUNT(DISTINCT b.id) FROM Benchmarks AS b
        JOIN Families AS fam ON fam.id = b.family
        WHERE b.logic LIKE ? AND b.category=? AND fam.firstOccurrence <= ?
        AND NOT b.isIncremental
        """,
        (args.logic, "industrial", yearstr),
    ):
        industrial.append(categoryRow[0])

    print(
        f"{year}; {this_solved}; {this_unsolved - this_solved}; {this_fresh - this_unsolved}"
    )

connection.close()

plt.style.use("seaborn-v0_8-muted")
fig, ax = plt.subplots(2, 1, layout="constrained")

stacks = ax[0].stackplot(
    range(5, 26), solved, unsolved, fresh, labels=["Solved", "Unsolved", "Fresh"]
)

# hatches=["\\\\", "xx",".."]
# for stack, hatch in zip(stacks, hatches):
#     stack.set_hatch(hatch)

ax[0].set(xlim=(5, 25), xticks=range(5, 26))
ax[0].legend(title="Status")
ax[0].set_ylabel("Benchmarks")
# ax.set_xlabel('Year (2005-2024)')
ax[0].set_xticklabels([])
ax[0].grid(True)

industrialNorm = []
craftedNorm = []
randomNorm = []
for ind, cra, ran in zip(industrial, crafted, random):
    total = ind + cra + ran
    industrialNorm.append(ind / total * 100)
    craftedNorm.append(cra / total * 100)
    randomNorm.append(ran / total * 100)

# fig, ax = plt.subplots()
stacks = ax[1].stackplot(
    range(5, 26),
    industrialNorm,
    craftedNorm,
    randomNorm,
    labels=["Industrial", "Crafted", "Random"],
)
# hatches=["\\\\", "xx",".."]
# for stack, hatch in zip(stacks, hatches):
#     stack.set_hatch(hatch)

ax[1].set(xlim=(5, 25), xticks=range(5, 26), ylim=(0, 100))
ax[1].legend(title="Category")
ax[1].set_ylabel("Percentage")
ax[1].set_xlabel("Year (2005-2025)")
ax[1].grid(True)

matplot2tikz.save("history.tex")
plt.show()
