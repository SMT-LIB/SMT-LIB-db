import re
import datetime
import subprocess
import json
import sqlite3
import os

import modules.solvers

script_dir = os.path.dirname(__file__)

def setup_benchmarks(connection):
    connection.execute(
        """CREATE TABLE Benchmarks(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        family INT,
        logic NVARCHAR(100) NOT NULL,
        isIncremental BOOL,
        size INT,
        compressedSize INT,
        license INT,
        generatedOn DATETIME,
        generatedBy TEXT,
        generator TEXT,
        timeLimit REAL,
        application TEXT,
        description TEXT,
        category TEXT,
        passesDolmen BOOL,
        passesDolmenStrict BOOL,
        queryCount INT NOT NULL,
        FOREIGN KEY(family) REFERENCES Families(id)
        FOREIGN KEY(license) REFERENCES Licenses(id)
        FOREIGN KEY(logic) REFERENCES Logics(logic)
    );"""
    )

    connection.execute(
        """CREATE TABLE Queries(
        id INTEGER PRIMARY KEY,
        benchmark INT,
        idx INT,
        normalizedSize INT,
        compressedSize INT,
        assertsCount INT,
        declareFunCount INT,
        declareConstCount INT,
        declareSortCount INT,
        defineFunCount INT,
        defineFunRecCount INT,
        constantFunCount INT,
        defineSortCount INT,
        declareDatatypeCount INT,
        maxTermDepth INT,
        status TEXT,
        inferredStatus TEXT,
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    );"""
    )

    connection.execute(
        """CREATE TABLE Families(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL,
        folderName TEXT NOT NULL,
        date DATE,
        firstOccurrence DATE,
        benchmarkCount INT NOT NULL,
        UNIQUE(folderName)
    );"""
    )

    connection.execute(
        """CREATE TABLE TargetSolvers(
        id INTEGER PRIMARY KEY,
        benchmark INTEGER NOT NULL,
        solverVariant INT NOT NULL,
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id),
        FOREIGN KEY(solverVariant) REFERENCES SolverVariants(id)
    );"""
    )

    # id is declared INT to force it to not be an alias to rowid
    connection.execute(
        """CREATE TABLE Symbols(
        id INT PRIMARY KEY,
        name TEXT);"""
    )

    connection.execute(
        """CREATE TABLE SymbolCounts(
        symbol INT,
        query INT,
        count INT NOT NULL,
        FOREIGN KEY(symbol) REFERENCES Symbols(id)
        FOREIGN KEY(query) REFERENCES Queries (id)
    );"""
    )

    with open(
        os.path.join(script_dir, "../klhm/src/smtlib-symbols"), "r"
    ) as symbolFile:
        count = 1
        for line in symbolFile:
            if line[0] == ";":
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO Symbols(id,name)
                VALUES(?,?);
                """,
                (
                    count,
                    line.strip(),
                ),
            )
            count = count + 1
        connection.commit()


def parse_family(name):
    """
    Parses the filename component that reperesents a family and a date.
    Possible cases are:
        yyyymmdd-NAME
        yyyy-NAME
        NAME
    """
    match = re.match(r"(\d\d\d\d)(\d\d)(\d\d)-(.*)", name)
    if match:
        try:
            return datetime.date(int(match[1]), int(match[2]), int(match[3])), match[4]
        except ValueError:
            return None, name
    match = re.match(r"(\d\d\d\d)-(.*)", name)
    if match:
        return datetime.date(int(match[1]), 1, 1), match[2]
    return None, name


def calculate_benchmark_count(connection):
    """
    Calculates the number of benchmarks in each family.
    """
    connection.execute(
        "UPDATE Families SET benchmarkCount = (SELECT COUNT(id) FROM Benchmarks WHERE Benchmarks.family=Families.id);"
    )
    connection.commit()


def get_license_id(connection, license):
    if license == None:
        license = "https://creativecommons.org/licenses/by/4.0/"
    license = license.replace("http:", "https:")
    for row in connection.execute(
        "SELECT id FROM Licenses WHERE name=? OR link=? OR spdxIdentifier=?",
        (license, license, license),
    ):
        return row[0]

    raise Exception("Could not determine license.")


def add_benchmark(dbFile, benchmark, dolmenPath):
    """
    Populates the database with the filenames of the benchmarks.
    Does not populate metadata fields or anything else.
    """
    print(f"Adding {benchmark}")
    parts = benchmark.parts

    incrementalCount = parts.count("incremental")
    nonincrementalCount = parts.count("non-incremental")
    count = incrementalCount + nonincrementalCount

    if count != 1:
        raise Exception(
            f"Benchmark path {benchmark} does not contain at most one 'incremental' or 'non-incremental'."
        )
    if incrementalCount > 0:
        parts = parts[parts.index("incremental") :]
        isIncremental = True
    else:
        parts = parts[parts.index("non-incremental") :]
        isIncremental = False

    logic = parts[1]
    familyFolder = parts[2]
    date, familyName = parse_family(familyFolder)
    fileName = "/".join(parts[3:])

    klhm = subprocess.run(
        os.path.join(script_dir, f"../klhm/zig-out/bin/klhm {benchmark}"),
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    klhmData = json.loads(klhm.stdout)
    queryObjs = klhmData[0:-1]
    benchmarkObj = klhmData[-1]

    generatedOn = None
    try:
        generatedOn = datetime.datetime.fromisoformat(benchmarkObj["generatedOn"])
    except (ValueError, TypeError):
        pass

    dolmen = subprocess.call(
        f"{dolmenPath} -s 4G --strict=false {benchmark}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if dolmen == 2 or dolmen == 125:
        dolmen = None
    elif dolmen == 0:
        dolmen = True
    else:
        dolmen = False

    dolmenStrict = subprocess.call(
        f"{dolmenPath} -s 4G --strict=true {benchmark}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if dolmenStrict == 2 or dolmenStrict == 125:
        dolmenStrict = None
    elif dolmenStrict == 0:
        dolmenStrict = True
    else:
        dolmenStrict = False

    if dolmenStrict is None or dolmen is None:
        print("Have none!")

    connection = sqlite3.connect(dbFile, timeout=30.0)
    # This should not be necessary, because WAL mode is persistent, but we
    # add it here to be sure.
    connection.execute("PRAGMA journal_mode=wal")
    # Disable to-disc syncing, might corrupt database on system crash, but since
    # this script is used to build the database upfront, this is mostly harmless.
    connection.execute("PRAGMA synchronous = OFF")

    cursor = connection.cursor()
    familyId = None
    # short circuit
    for row in cursor.execute(
        "SELECT id FROM Families WHERE folderName=?", (familyFolder,)
    ):
        familyId = row[0]

    if not familyId:
        cursor.execute(
            """
            INSERT OR IGNORE INTO Families(name, foldername, date, benchmarkCount)
            VALUES(?,?,?,?);
            """,
            (familyName, familyFolder, date, 0),
        )
        familyId = cursor.lastrowid

    licenseId = get_license_id(connection, benchmarkObj["license"])
    timeLimit = 0.0
    try:
        timeLimit = float(benchmarkObj["timeLimit"])
    except:
        pass

    cursor.execute(
        """
        INSERT INTO Benchmarks(name,
                               family,
                               logic,
                               isIncremental,
                               size,
                               compressedSize,
                               license,
                               generatedOn,
                               generatedBy,
                               generator,
                               timeLimit,
                               application,
                               description,
                               category,
                               passesDolmen,
                               passesDolmenStrict,
                               queryCount)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """,
        (
            fileName,
            familyId,
            benchmarkObj["logic"],
            benchmarkObj["isIncremental"],
            benchmarkObj["size"],
            benchmarkObj["compressedSize"],
            licenseId,
            generatedOn,
            benchmarkObj["generatedBy"],
            benchmarkObj["generator"],
            timeLimit,
            benchmarkObj["application"],
            benchmarkObj["description"],
            benchmarkObj["category"],
            dolmen,
            dolmenStrict,
            benchmarkObj["queryCount"],
        ),
    )
    benchmarkId = cursor.lastrowid

    if benchmarkObj["targetSolver"]:
        targetSolvers = benchmarkObj["targetSolver"]
        # Hacks for the two space sperated cases
        if targetSolvers == "Boolector Z3 STP":
            targetSolvers = ["Boolector", "Z3", "STP"]
        elif targetSolvers == "CVC4 Mathsat SPASS-IQ YICES Z3":
            targetSolvers = ["CVC4", "Mathsat", "SPASS-IQ", "YICES", "Z3"]
        else:
            # Split on '/', " or ", and ","
            targetSolvers = targetSolvers.replace("/", ",")
            targetSolvers = targetSolvers.replace(" or ", ",")
            targetSolvers = targetSolvers.split(",")
            targetSolvers = map(lambda x: x.strip(), targetSolvers)
        for targetSolver in targetSolvers:
            try:
                id = modules.solvers.global_variant_lookup[targetSolver]
                cursor.execute(
                    """
                       INSERT INTO TargetSolvers(benchmark,
                                                 solverVariant)
                       VALUES(?,?);
                       """,
                    (benchmarkId, id),
                )
            except KeyError:
                print(f"WARNING: Target solver '{targetSolver}' not known.")
        connection.commit()

    for idx in range(len(queryObjs)):
        queryObj = queryObjs[idx]
        cursor.execute(
            """
            INSERT INTO Queries(benchmark,
                                idx,
                                normalizedSize,
                                compressedSize,
                                assertsCount,
                                declareFunCount,
                                declareConstCount,
                                declareSortCount,
                                defineFunCount,
                                defineFunRecCount,
                                constantFunCount,
                                defineSortCount,
                                declareDatatypeCount,
                                maxTermDepth,
                                status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """,
            (
                benchmarkId,
                idx + 1,
                queryObj["normalizedSize"],
                queryObj["compressedSize"],
                queryObj["assertsCount"],
                queryObj["declareFunCount"],
                queryObj["declareConstCount"],
                queryObj["declareSortCount"],
                queryObj["defineFunCount"],
                queryObj["defineFunRecCount"],
                queryObj["constantFunCount"],
                queryObj["defineSortCount"],
                queryObj["declareDatatypeCount"],
                queryObj["maxTermDepth"],
                queryObj["status"],
            ),
        )
        queryId = cursor.lastrowid
        symbolCounts = queryObj["symbolFrequency"]
        for symbolIdx in range(len(symbolCounts)):
            if symbolCounts[symbolIdx] > 0:
                connection.execute(
                    """
                    INSERT INTO SymbolCounts(symbol,
                                             query,
                                             count)
                    VALUES(?,?,?);
                    """,
                    (symbolIdx + 1, queryId, symbolCounts[symbolIdx]),
                )
    connection.commit()
    connection.close()


def guess_benchmark_id(
    connection, isIncremental, logic, familyFoldername, fullFilename
):
    """
    Guess the id of a benchmark.  The guessing is necessary, because
    benchmarks might have moved paths between competitions.  The function
    first tests whether there one unique benchmark with a subset of the
    parameters.  First, it uses only `fullFilename`, then additionally
    `familyFoldername`, then additionally `isIncremental`
    then `logic`.
    The `isIncremental` field is always enforced.
    If any of these thests returns one unique benchmark, its id is
    returned.  If any returns non, or if all return more than one
    benchmark, None is returned.

    The priorities are informed by how often a component of the path change.
    E.g., the logic changed in the past for some benchmarks, because they were
    missclassified.
    """

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks WHERE name=?
        """,
        (fullFilename,),
    )
    l = r.fetchall()
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Families ON Families.Id = Benchmarks.family
            WHERE Benchmarks.name=? AND Families.folderName=?
        """,
        (fullFilename, familyFoldername),
    )
    l = r.fetchall()
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Families ON Families.Id = Benchmarks.family
            WHERE Benchmarks.name=? AND isIncremental=? AND Families.folderName=?
        """,
        (fullFilename, isIncremental, familyFoldername),
    )
    l = r.fetchall()
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Families ON Families.Id = Benchmarks.family
            WHERE Benchmarks.name=? AND logic=? AND isIncremental=? AND Families.folderName=?
        """,
        (fullFilename, logic, isIncremental, familyFoldername),
    )
    l = r.fetchall()
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    return None


def guess_query_id(
    connection, logic, familyFoldername, fullFilename, stats=None, isIncremental=False
):
    """
    Same as guess_benchmark_id, but returns the id of the sole query
    of a non-incremental benchmark.
    """
    if stats:
        stats["lookups"] = stats["lookups"] + 1
        stats["benchmarks"].add((logic, familyFoldername, fullFilename))
    benchmarkId = guess_benchmark_id(
        connection, isIncremental, logic, familyFoldername, fullFilename
    )
    if not benchmarkId:
        if stats:
            stats["lookupFailures"] = stats["lookupFailures"] + 1
            stats["unkownBenchmarks"].add((logic, familyFoldername, fullFilename))
        return None
    for r in connection.execute(
        """
        SELECT Id FROM Queries WHERE benchmark=?
        """,
        (benchmarkId,),
    ):
        return r[0]
    return None
