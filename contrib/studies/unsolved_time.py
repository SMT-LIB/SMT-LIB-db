#!/usr/bin/env python3

import argparse
import sqlite3
import statistics

parser = argparse.ArgumentParser()

parser.add_argument("database")
parser.add_argument("--logic", default="ALL")

args = parser.parse_args()

if args.logic == "ALL":
    args.logic = "%"

connection = sqlite3.connect(args.database)

# Get age of completely unsovled benchmarks
res = connection.execute(
    """
    SELECT fam.firstOccurrence FROM Benchmarks AS bnch
    JOIN Queries  AS qr  ON qr.benchmark = bnch.id
    JOIN Families AS fam ON fam.id = bnch.family
    WHERE NOT bnch.isIncremental
    AND bnch.logic LIKE ?
    AND NOT EXISTS (
        SELECT * FROM Results AS res WHERE
            (res.status == 'sat' OR res.status == 'unsat')
        AND res.query = qr.id
    );
    """,
    (args.logic,),
)

dates = res.fetchall()
count = 0
yearold = []
for date in dates:
    year = str(date[0])[0:4]
    if not year == "None":
        count = count + 1
        yearold.append(2025 - int(year))

print("Age of currently unsolved benchmarks.")
print(f"Data for {count} benchmarks.")
print(f"Max: {max(yearold):.2f}")
print(f"Min: {min(yearold):.2f}")
print(f"Mean: {statistics.mean(yearold):.2f}")
print(f"Median: {statistics.median(yearold):.2f}")
print(f"Geometric Mean: {statistics.geometric_mean(yearold):.2f}")

# Get distance between first occurence and solving time
res = connection.execute(
    """
    SELECT bnch.id, MIN(CAST(strftime('%Y', eval.date) as INTEGER) - CAST(strftime('%Y', fam.firstOccurrence) as INTEGER))  FROM Benchmarks AS bnch
    JOIN Queries  AS qr  ON qr.benchmark = bnch.id
    JOIN Families AS fam ON fam.id = bnch.family
    JOIN Results AS res ON res.query = qr.id
    JOIN Evaluations as eval ON eval.id = res.evaluation
    WHERE NOT bnch.isIncremental
    AND bnch.logic LIKE ?
    AND (res.status == 'sat' OR res.status == 'unsat')
    GROUP BY bnch.id;
    """,
    (args.logic,),
)

dates = res.fetchall()
yeardiff = list(filter(lambda x: x < 50 and x > 0, map(lambda x: x[1], dates)))

print("\nYears until benchmark is solved if not solved immediately.")
print(f"Data for {len(yeardiff)} benchmarks.")
print(f"Max: {max(yeardiff):.2f}")
print(f"Min: {min(yeardiff):.2f}")
print(f"Mean: {statistics.mean(yeardiff):.2f}")
print(f"Median: {statistics.median(yeardiff):.2f}")
print(f"Geometric Mean: {statistics.geometric_mean(yeardiff):.2f}")
