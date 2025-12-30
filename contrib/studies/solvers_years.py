#!/usr/bin/env python3

import argparse
import sqlite3
import statistics
import matplotlib.pyplot as plt
import matplot2tikz

"""
    Prints the number of solvers that participated in each evaluation
    (per logic).
"""


parser = argparse.ArgumentParser()

parser.add_argument("database")

args = parser.parse_args()

connection = sqlite3.connect(args.database)

years = list(range(2005, 2025))

res = connection.execute("SELECT DISTINCT logic FROM Benchmarks")
# logics = res.fetchall()
# logics.append(("%",))
logics = [("%",)]

res = connection.execute("SELECT id,name,date FROM Evaluations")
evaluations = res.fetchall()

print("Date;Evaluation", end="")
for (logic,) in logics:
    print(f";{logic}", end="")
print("")

overall_solvers = []
for evalId, evalName, evalDate in evaluations:
    print(f"{evalDate};{evalName}", end="")
    for (logic,) in logics:
        for logicSolversRow in connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) FROM Solvers AS s
                INNER JOIN SolverVariants AS sv ON sv.solver = s.id
                INNER JOIN Results AS r ON sv.id = r.solverVariant
                INNER JOIN Benchmarks AS b ON b.id = r.query
            WHERE b.logic LIKE ? AND r.evaluation=? AND b.isIncremental=0
            """,
            (logic, evalId),
        ):
            print(f";{logicSolversRow[0]}", end="")
        if logic == "%" and not evalDate == 2024:
            print("Add")
            overall_solvers.append(logicSolversRow[0])
    print("")

plt.style.use("seaborn-v0_8-muted")
fig, ax = plt.subplots()
ax.plot(range(5, 26), overall_solvers, ".-", linewidth=2)

ax.set(xlim=(5, 25), xticks=range(5, 25))
ax.set_ylabel("Solvers")
ax.set_xlabel("Year (2005-2025)")
ax.grid(True)

matplot2tikz.save("solvers.tex")
plt.show()
