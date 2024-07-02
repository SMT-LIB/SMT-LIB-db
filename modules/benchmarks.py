import re
import datetime
import subprocess
import mmap
import json

import modules.solvers


def setup_benchmarks(connection):
    connection.execute(
        """CREATE TABLE Benchmarks(
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL,
        benchmarkSet INT,
        logic NVARCHAR(100) NOT NULL,
        isIncremental BOOL,
        size INT,
        compressedSize INT,
        license INT,
        generatedOn DATETTIME,
        generatedBy TEXT,
        generator TEXT,
        application TEXT,
        description TEXT,
        category TEXT,
        subbenchmarkCount INT NOT NULL,
        FOREIGN KEY(benchmarkSet) REFERENCES Sets(id)
        FOREIGN KEY(license) REFERENCES Licenses(id)
    );"""
    )

    connection.execute(
        """CREATE TABLE Subbenchmarks(
        id INTEGER PRIMARY KEY,
        benchmark INT,
        number INT,
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

        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    );"""
    )

    connection.execute(
        """CREATE TABLE Sets(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL,
        folderName TEXT NOT NULL,
        date DATE,
        benchmarkCount INT NOT NULL,
        UNIQUE(folderName)
    );"""
    )

    connection.execute(
        """CREATE TABLE TargetSolvers(
        id INTEGER PRIMARY KEY,
        benchmark INTEGER NOT NULL,
        solverVariant TEXT NOT NULL,
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
        """CREATE TABLE SymbolsCounts(
        symbol INT,
        subbenchmark INT,
        count INT NOT NULL,
        FOREIGN KEY(symbol) REFERENCES Symbols(id)
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    );"""
    )

    with open("./klhm/src/smtlib-symbols", "r") as symbolFile:
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


def parse_set(name):
    """
    Parses the filename component that reperesents a set and a date.
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
    Calculates the number of benchmarks in each set.
    """
    connection.execute(
        "UPDATE Sets SET benchmarkCount = (SELECT COUNT(id) FROM Benchmarks WHERE Benchmarks.benchmarkSet=Sets.id);"
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


def add_benchmark(connection, benchmark):
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
    setFolder = parts[2]
    date, setName = parse_set(setFolder)
    fileName = "/".join(parts[3:])

    cursor = connection.cursor()
    setId = None
    # short circuit
    for row in cursor.execute("SELECT id FROM Sets WHERE folderName=?", (setFolder,)):
        setId = row[0]

    if not setId:
        cursor.execute(
            """
            INSERT OR IGNORE INTO Sets(name, foldername, date, benchmarkCount)
            VALUES(?,?,?,?);
            """,
            (setName, setFolder, date, 0),
        )
        setId = cursor.lastrowid

    klhm = subprocess.run(
        f"./klhm/zig-out/bin/klhm {benchmark}",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    klhmData = json.loads(klhm.stdout)
    subbenchmarkObjs = klhmData[0:-1]
    benchmarkObj = klhmData[-1]

    licenseId = get_license_id(connection, benchmarkObj["license"])

    generatedOn = None
    try:
        generatedOn = datetime.datetime.fromisoformat(benchmarkObj["generatedOn"])
    except (ValueError, TypeError):
        pass

    cursor.execute(
        """
        INSERT INTO Benchmarks(filename,
                               benchmarkSet,
                               logic,
                               isIncremental,
                               size,
                               compressedSize,
                               license,
                               generatedOn,
                               generatedBy,
                               generator,
                               application,
                               description,
                               category,
                               subbenchmarkCount)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """,
        (
            fileName,
            setId,
            benchmarkObj["logic"],
            benchmarkObj["isIncremental"],
            benchmarkObj["size"],
            benchmarkObj["compressedSize"],
            licenseId,
            generatedOn,
            benchmarkObj["generatedBy"],
            benchmarkObj["generator"],
            benchmarkObj["application"],
            benchmarkObj["description"],
            benchmarkObj["category"],
            benchmarkObj["subbenchmarkCount"],
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

    for idx in range(len(subbenchmarkObjs)):
        subbenchmarkObj = subbenchmarkObjs[idx]
        cursor.execute(
            """
            INSERT INTO Subbenchmarks(benchmark,
                                      number,
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
                subbenchmarkObj["normalizedSize"],
                subbenchmarkObj["compressedSize"],
                subbenchmarkObj["assertsCount"],
                subbenchmarkObj["declareFunCount"],
                subbenchmarkObj["declareConstCount"],
                subbenchmarkObj["declareSortCount"],
                subbenchmarkObj["defineFunCount"],
                subbenchmarkObj["defineFunRecCount"],
                subbenchmarkObj["constantFunCount"],
                subbenchmarkObj["defineSortCount"],
                subbenchmarkObj["declareDatatypeCount"],
                subbenchmarkObj["maxTermDepth"],
                subbenchmarkObj["status"],
            ),
        )
        subbenchmarkId = cursor.lastrowid
        symbolCounts = subbenchmarkObj["symbolFrequency"]
        for symbolIdx in range(len(symbolCounts)):
            if symbolCounts[symbolIdx] > 0:
                connection.execute(
                    """
                    INSERT INTO SymbolsCounts(symbol,
                                              subbenchmark,
                                              count)
                    VALUES(?,?,?);
                    """,
                    (symbolIdx + 1, subbenchmarkId, symbolCounts[symbolIdx]),
                )
    connection.commit()


def guess_benchmark_id(connection, fullFilename, isIncremental=None):
    """
    Guess the id of a benchmark from a path
    "[non-]incremental/LOGIC/SETFOLDERNAME/BENCHMARKPATH".  The guessing is
    necessary, because benchmarks might have moved paths between competitions.
    The function first tests whether there one unique benchmark with a subset
    of the parameters.  First, it uses only "BENCHMARKPATH", then
    additionally SETFOLDERNAME, then additionally isIncremental
    then LOGIC.
    If any of these thests returns one unique benchmark, its id is returned.
    If any returns non, or if all return more than one benchmark,
    None is returned.

    The priorities are informed by how often a component of the path change.
    E.g., the LOGIC changed in the past for some benchmarks, because they were
    missclassified.

    If `isIncremental` is given, the `fullFilepath` should not contain
    the `[non-]incremental` part.

    """
    if isIncremental == None:
        slashIdx = fullFilename.find("/")
        if fullFilename[:slashIdx] == "non-incremental":
            isIncremental = False
        else:
            isIncremental = True
        fullFilename = fullFilename[slashIdx + 1 :]

    slashIdx = fullFilename.find("/")
    logic = fullFilename[:slashIdx]
    fullFilename = fullFilename[slashIdx + 1 :]

    slashIdx = fullFilename.find("/")
    setFoldername = fullFilename[:slashIdx]
    fullFilename = fullFilename[slashIdx + 1 :]

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks WHERE filename=?
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
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Sets ON Sets.Id = Benchmarks.benchmarkSet
            WHERE filename=? AND Sets.folderName=?
        """,
        (fullFilename, setFoldername),
    )
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]

    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Sets ON Sets.Id = Benchmarks.benchmarkSet
            WHERE filename=? AND isIncremental=? AND Sets.folderName=?
        """,
        (fullFilename, isIncremental, setFoldername),
    )
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    r = connection.execute(
        """
        SELECT Benchmarks.Id FROM Benchmarks INNER JOIN Sets ON Sets.Id = Benchmarks.benchmarkSet
            WHERE filename=? AND logic=? AND isIncremental=? AND Sets.folderName=?
        """,
        (fullFilename, isIncremental, logic, setFoldername),
    )
    if len(l) == 0:
        return None
    if len(l) == 1:
        return l[0][0]
    return None
