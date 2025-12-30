import re

rex = re.compile(r"WARNING: Benchmark ([^\s]+\.smt2) of SMT-COMP (\d+) not found \(([A-Z_]+), ([^\s]+)\).*")

with open("20250326-postpoplog", 'r') as log:
    year = None
    coll = {}
    for l in log.readlines():
        res = rex.match(l)
        if res:
            if res[2] != year:
                print(year)
                print(coll)
                year = res[2]
                coll = {}
            if res[4] in coll:
                coll[res[4]] = coll[res[4]] + 1
            else:
                coll[res[4]] = 1
    print(year)
    print(coll)
