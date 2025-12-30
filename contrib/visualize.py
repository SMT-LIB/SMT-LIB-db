#!/usr/bin/env python3

import sqlite3

connection = sqlite3.connect("smtlib-20250718-postpop.sqlite")

years = list(range(2005, 2025))

for year in years:
    yearstr = f"{year}-12-31"
    oldyearstr = f"{year-1}-12-31"
    for row in connection.execute("""
        SELECT COUNT(bnch.id) FROM Benchmarks as bnch join Families as fam on fam.id = bnch.family
        where not bnch.isIncremental and fam.firstOccurrence <= ?;
        """,
        (yearstr,),
    ):
        total = row[0]
    for row in connection.execute("""
        SELECT count(DISTINCT bnch.id) FROM Benchmarks as bnch
        join Families as fam on fam.id = bnch.family
        join Queries as qr on qr.benchmark = bnch.id
        join Results as res on res.query = qr.id
        join Evaluations as eval on eval.id = res.evaluation
        where not bnch.isIncremental and fam.firstOccurrence <= ? and eval.date <= ?;
        """,
        (yearstr,oldyearstr),
    ):
        used = row[0]
    for row in connection.execute("""
        SELECT count(DISTINCT bnch.id) FROM Benchmarks as bnch
        join Families as fam on fam.id = bnch.family
        join Queries as qr on qr.benchmark = bnch.id
        join Results as res on res.query = qr.id
        join Evaluations as eval on eval.id = res.evaluation
        where not bnch.isIncremental and fam.firstOccurrence <= ? and eval.date <= ?
        and (res.status == 'sat' or res.status == 'unsat');
        """,
        (yearstr,oldyearstr),
    ):
        solved = row[0]

    print(year, total, used, solved)
# number of benchmarks:
# SELECT COUNT(bnch.id) FROM Benchmarks as bnch join Families as fam on fam.id = bnch.family
# where not bnch.isIncremental and fam.firstOccurrence <= '2024-12-31';

# number of used benchmarks:
# SELECT count(DISTINCT bnch.id) FROM Benchmarks as bnch
# join Families as fam on fam.id = bnch.family
# join Queries as qr on qr.benchmark = bnch.id
# join Results as res on res.query = qr.id
# join Evaluations as eval on eval.id = res.evaluation
# where not bnch.isIncremental and fam.firstOccurrence <= '2023-12-31' and eval.date <= '2023-12-31';

# solved
# SELECT count(DISTINCT bnch.id) FROM Benchmarks as bnch
# join Families as fam on fam.id = bnch.family
# join Queries as qr on qr.benchmark = bnch.id
# join Results as res on res.query = qr.id
# join Evaluations as eval on eval.id = res.evaluation
# where not bnch.isIncremental and fam.firstOccurrence <= '2023-12-31' and eval.date <= '2023-12-31'
# and (res.status == 'sat' or res.status == 'unsat');

connection.close()
