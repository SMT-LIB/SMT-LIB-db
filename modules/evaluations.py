import tempfile
import subprocess
import json
import csv
import re
import sqlite3

from pathlib import Path
from modules import benchmarks
from bs4 import BeautifulSoup

import modules.solvers
from modules.fixup import *


def setup_evaluations(connection):
    connection.execute(
        """CREATE TABLE Evaluations(
        id INTEGER PRIMARY KEY,
        name TEXT,
        date DATE,
        link TEXT,
        hardwareRevision INT,
        wallclockLimit REAL,
        memoryLimit REAL
        );"""
    )

    connection.execute(
        """CREATE TABLE Results(
        id INTEGER PRIMARY KEY,
        evaluation INTEGER,
        query INT,
        solverVariant INT,
        cpuTime REAL,
        wallclockTime REAL,
        status TEXT,
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        FOREIGN KEY(query) REFERENCES Queries(id)
        FOREIGN KEY(solverVariant) REFERENCES SolverVariants(id)
        );"""
    )

    connection.execute(
        """CREATE TABLE Ratings(
        id INTEGER PRIMARY KEY,
        query INT,
        evaluation INT,
        rating REAL,
        consideredSolvers INT,
        successfulSolvers INT,
        FOREIGN KEY(query) REFERENCES Queries(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        );"""
    )


def write_result(
    connection, evaluationId, solver, queryId, outcome, cpuTime, wallclockTime
):
    solverVariantId = None
    for r in connection.execute(
        """
            SELECT Id FROM SolverVariants WHERE fullName=? AND evaluation=?
            """,
        (solver, evaluationId),
    ):
        solverVariantId = r[0]
    if not solverVariantId:
        # We do not care about the results from solvers that are not on the list.
        # Note that some solvers are omitted on purpose, for example
        # if there is a fixed version.
        return
    connection.execute(
        """
            INSERT INTO Results(evaluation, query, solverVariant, cpuTime, wallclockTime, status)
            VALUES(?,?,?,?,?,?);
            """,
        (
            evaluationId,
            queryId,
            solverVariantId,
            cpuTime,
            wallclockTime,
            outcome,
        ),
    )


def make_stats_dict(name):
    return {
        "name": name,
        "lookups": 0,
        "lookupFailures": 0,
        "withCandidates": set(),
        "benchmarks": set(),
        "unkownBenchmarks": set(),
    }


def print_stats_dict(stats):
    lookupPercentage = stats["lookupFailures"] / stats["lookups"] * 100.0
    benchmarkPercentage = (
        len(stats["unkownBenchmarks"]) / len(stats["benchmarks"]) * 100.0
    )
    print(
        f"{stats['name']}\t\tMissing entries: {stats['lookupFailures']} {lookupPercentage:.2f}% Unknown Benchmark: {len(stats['unkownBenchmarks'])} {benchmarkPercentage:.2f}% Benchmarks: {len(stats['benchmarks'])} Lookups: {stats['lookups']}"
    )
    # for c in stats["withCandidates"]:
    #     print(c)


def benchmark_status(solved_status):
    if solved_status in ["-", "starexec-unknown"]:
        return "unknown"
    if not solved_status in ["sat", "unsat"]:
        return "unknown"
    return solved_status


old_header_regex = r"^Detailed results for (.+) at ([A-Z0-9_]+)$"


def add_smt_comp_early(connection, year, date):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
    # Date is the day the PDPAR (pre. SMT) workshop happened.
    if year == "2005":
        cursor = connection.execute(
            """
            INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit, memoryLimit)
            VALUES(?,?,?,?,?,?);
            """,
            (
                name,
                date,
                f"https://smtcomp.sourceforge.net/{year}/",
                6,
                13.3 * 60,
                0.45,
            ),
        )
        evaluationId = cursor.lastrowid
    else:
        cursor = connection.execute(
            """
            INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit, memoryLimit)
            VALUES(?,?,?,?,?,?);
            """,
            (name, date, f"https://smtcomp.sourceforge.net/{year}/", 5, 20 * 60, 1.5),
        )
        evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding SMT-COMP {year} results")
    for htmlFile in Path(f"./data/early-SMT-COMP/{year}").glob("results-*-*.shtml"):
        soup = BeautifulSoup(open(htmlFile), "html.parser")
        header = re.match(old_header_regex, soup.find("h1").text)
        solver = header[1]
        logic = header[2]

        # Legacy logic, no longer used.
        if logic == "QF_UFBV32":
            logic = "QF_BV"  # TODO: QF_UFBV?

        table = soup.find("table", "score")
        if not table:
            table = soup.find("table", "score2")
        for c in table.find_all("tr"):
            tds = list(c.find_all("td"))
            # the header
            if len(tds) == 0:
                continue
            assert len(tds) == 4
            correct = tds[3].text
            if not correct == "yes":
                answer = "unknown"
            else:
                answer = tds[1].text

            try:
                time = float(tds[2].text)
            except ValueError:
                time = float("NaN")

            benchmarkFields = tds[0].text.split("/")
            benchmarkFamily = benchmarkFields[0]
            benchmarkName = "/".join(benchmarkFields[1:]) + "2"

            (logic, benchmarkFamily, benchmarkName) = fix_smt_comp_early(
                logic, benchmarkFamily, benchmarkName
            )
            queryId = benchmarks.guess_query_id(
                connection, logic, benchmarkFamily, benchmarkName, stats
            )
            if not queryId:
                print(
                    f"WARNING: Benchmark {benchmarkName} of SMT-COMP {year} not found ({logic}, {benchmarkFamily})"
                )
                continue

            write_result(
                connection,
                evaluationId,
                solver,
                queryId,
                answer,
                None,
                time,
            )
    return stats


def add_smtexec(
    connection,
    smtexecConnection,
    year,
    date,
    jobId,
    cmpHardware,
    cmpTimeout=None,
    cmpMem=None,
):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit, memoryLimit)
        VALUES(?,?,?,?,?,?);
        """,
        (
            name,
            date,
            f"https://smt-comp.github.io/{year}/",
            cmpHardware,
            cmpTimeout,
            cmpMem,
        ),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding smtexec SMT-COMP {year} results")
    for r in smtexecConnection.execute(
        """
        SELECT solvers.displayname, divisions.name, benchmarks.file, time, solversolution
        FROM results
        INNER JOIN benchmarks ON benchmarks.benchmarkid == results.benchmarkid
        INNER JOIN solvers ON solvers.solverid == results.solverid
        INNER JOIN divisions ON divisions.divisionid == benchmarks.divisionid
        WHERE jobid=?
            """,
        (jobId,),
    ):
        solver = r[0]
        logic = r[1]
        benchmarkField = r[2].split("/")
        benchmarkFamily = benchmarkField[0]
        benchmarkName = "/".join(benchmarkField[1:])
        # Early competitions were using SMT-LIB 1
        if benchmarkName[-1] != "2":
            benchmarkName = benchmarkName + "2"
        time = float(r[3])
        outcome = benchmark_status(r[4])
        queryId = benchmarks.guess_query_id(
            connection, logic, benchmarkFamily, benchmarkName, stats
        )
        if not queryId:
            print(
                f"WARNING: Benchmark {benchmarkName} of SMT-COMP {year} not found ({logic}, {benchmarkFamily})"
            )
            continue
        write_result(
            connection,
            evaluationId,
            solver,
            queryId,
            outcome,
            None,
            time,
        )
    connection.commit()
    return stats


# CSV format used for smt eval 2013
def add_smt_eval_2013(connection, csvDataFile):
    name = f"SMT Evaluation 2013"
    stats = make_stats_dict(name)
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit)
        VALUES(?,?,?,?,?);
        """,
        (name, "2013-07-02", f"https://smtcomp.sourceforge.net/2013/", 2, 25 * 60),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()

    # Maps benchmark ids in the csv to ids in the database.
    # This is necessary for the "FillInRun"s that don't contain full filenames.
    # TODO: this could be an optimization for the other formats
    # "FillInRun" are 593 the pairs originally omitted due to a "bug" (see paper).
    benchmarkIdMapping = {}

    print(f"Adding SMT Evaluation 2013 results")
    with open(csvDataFile, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            solver = f"{row[' solver']} {row['configuration']}"
            # This is wallclock time. It tops out at 1500s, which is the
            # wallclock time limit specified n the paper.
            time = row["time(s)"]
            if time == "-":
                time = float("NaN")
            else:
                time = float(time)

            status = row["result"]
            status = benchmark_status(status)
            benchmarkField = row[" benchmark"].split("/")
            if row["benchmark id"] in benchmarkIdMapping:
                stats["lookups"] = stats["lookups"] + 1
                queryId = benchmarkIdMapping[row["benchmark id"]]
            else:
                if benchmarkField[0] == "FillInRun":
                    print(
                        f"WARNING: Fill in run {row[' benchmark']} of SMT Evaluation 2013 not found"
                    )
                    stats["lookupFailures"] = stats["lookupFailures"] + 1
                    continue

                logic = benchmarkField[1]
                benchmarkFamily = benchmarkField[2]
                benchmarkName = "/".join(benchmarkField[3:])

                queryId = benchmarks.guess_query_id(
                    connection, logic, benchmarkFamily, benchmarkName, stats
                )
                if not queryId:
                    print(
                        f"WARNING: Benchmark {benchmarkName} of SMT Evaluation 2013 not found"
                    )
                    continue
                benchmarkIdMapping[row["benchmark id"]] = queryId

            write_result(
                connection,
                evaluationId,
                solver,
                queryId,
                status,
                None,
                time,
            )
    connection.commit()
    return stats


# CSV format used 2014
def add_smt_comp_2014(connection, compressedCsvFilename):
    name = f"SMT-COMP 2014"
    stats = make_stats_dict(name)
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit, memoryLimit)
        VALUES(?,?,?,?,?,?);
        """,
        (name, "2014-07-21", f"https://smt-comp.github.io/2014/", 2, 25 * 60, 100),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding SMT-COMP 2014 results")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"tar -xf '{compressedCsvFilename}'",
            cwd=tmpdir,
            shell=True,
        )
        csvName = Path(compressedCsvFilename.stem).stem
        with open(f"{tmpdir}/{csvName}.csv", newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for row in reader:
                solver = f"{row[3]} {row[5]}"
                cpuTime = row[8]
                wallclockTime = row[9]
                status = row[10]
                status = benchmark_status(status)
                benchmarkField = row[1].split("/")
                logic = benchmarkField[0]
                benchmarkFamily = benchmarkField[1]
                benchmarkName = "/".join(benchmarkField[2:])
                queryId = benchmarks.guess_query_id(
                    connection, logic, benchmarkFamily, benchmarkName, stats
                )
                if not queryId:
                    print(
                        f"WARNING: Benchmark {benchmarkName} of SMT-COMP 2014 not found ({logic}, {benchmarkFamily})"
                    )
                    continue
                write_result(
                    connection,
                    evaluationId,
                    solver,
                    queryId,
                    status,
                    cpuTime,
                    wallclockTime,
                )
    connection.commit()
    return stats


# CSV format used 2015-2017
def add_smt_comp_oldstyle(connection, compressedCsvFilename, year, date):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
    timeLimit = 20 * 60 if year == "2017" else 40 * 60
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit, memoryLimit)
        VALUES(?,?,?,?,?,?);
        """,
        (name, date, f"https://smt-comp.github.io/{year}/", 2, timeLimit, 60),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding oldstyle SMT-COMP {year} results")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"tar -xf '{compressedCsvFilename}'",
            cwd=tmpdir,
            shell=True,
        )
        csvName = Path(compressedCsvFilename.stem).stem
        with open(f"{tmpdir}/{csvName}.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            for row in reader:
                solver = f"{row['solver']} {row['configuration']}"
                cpuTime = row["cpu time"]
                wallclockTime = row["wallclock time"]
                status = row["result"]
                status = benchmark_status(status)
                benchmarkField = row["benchmark"].replace("Other Divisions/", "")
                benchmarkField = benchmarkField.replace("Datatype Divisions/", "")
                benchmarkField = benchmarkField.split("/")
                logic = benchmarkField[0]
                benchmarkFamily = benchmarkField[1]
                benchmarkName = "/".join(benchmarkField[2:])
                (logic, benchmarkFamily, benchmarkName) = fix_2017_preiner(
                    logic, benchmarkFamily, benchmarkName
                )
                queryId = benchmarks.guess_query_id(
                    connection, logic, benchmarkFamily, benchmarkName, stats
                )
                if not queryId:
                    print(
                        f"WARNING: Benchmark {benchmarkName} of SMT-COMP {year} not found ({logic}, {benchmarkFamily})"
                    )
                    continue
                write_result(
                    connection,
                    evaluationId,
                    solver,
                    queryId,
                    status,
                    cpuTime,
                    wallclockTime,
                )
    connection.commit()
    return stats


def add_smt_comp_generic(connection, folder, year, date):
    name = f"SMT-COMP {year}"
    stats = make_stats_dict(name)
    hardwareRevision = 1 if int(year) >= 2024 else 2
    timeLimit = 40 * 60 if year == "2019" else 20 * 60
    cursor = connection.execute(
        """
        INSERT INTO Evaluations(name, date, link, hardwareRevision, wallclockLimit, memoryLimit)
        VALUES(?,?,?,?,?,?);
        """,
        (
            name,
            date,
            f"https://smt-comp.github.io/{year}/",
            hardwareRevision,
            timeLimit,
            30,
        ),
    )
    evaluationId = cursor.lastrowid
    modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)
    connection.commit()
    print(f"Adding SMT-COMP {year} results")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"gunzip -fk {folder}/data/results-sq-{year}.json.gz",
            shell=True,
        )
        with open(f"{folder}/data/results-sq-{year}.json") as resultfile:
            jsonObject = json.load(resultfile)
            results = jsonObject["results"]
            for result in results:
                assert result["track"] == "SingleQuery"
                solver = result["solver"]

                fileField = result["file"]
                familyField = fileField["family"][0]
                fullbench = "/".join(fileField["family"][1:] + [fileField["name"]])

                queryId = benchmarks.guess_query_id(
                    connection, fileField["logic"], familyField, fullbench, stats
                )
                if not queryId:
                    print(
                        f"WARNING: Benchmark {fullbench} of SMT-COMP {year} not found ({fileField['logic']}, {familyField})"
                    )
                    continue
                cpuTime = result["cpu_time"]
                wallclockTime = result["wallclock_time"]
                status = benchmark_status(result["result"])
                write_result(
                    connection,
                    evaluationId,
                    solver,
                    queryId,
                    status,
                    cpuTime,
                    wallclockTime,
                )

    connection.commit()
    return stats


def add_smt_comp_inc_starexec(connection, year, starexecfolder):
    name = f"SMT-COMP {year}"
    for r in connection.execute(
        """
        SELECT Id FROM Evaluations WHERE name=?
        """,
        (name,),
    ):
        evaluationId = r[0]
    print(f"Adding SMT-COMP {year} incremental results")
    path = Path(starexecfolder) / f"{year}"
    for p in path.glob("*.zip"):
        print(f"\tProcessing {p}")
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                f"unzip '{p}'",
                cwd=tmpdir,
                shell=True,
                stdout=subprocess.DEVNULL,
            )
            for logfile in Path(tmpdir).glob("**/*.txt"):
                logpath = logfile.relative_to(tmpdir)

                benchfile = logpath.parts[-2]
                benchfolder = logpath.parts[4:-3]
                benchmark = Path(*benchfolder) / benchfile

                solver = logpath.parts[-3]
                logic = logpath.parts[2]
                family = logpath.parts[3]
                solverVariantId = None
                for r in connection.execute(
                    """
                        SELECT Id FROM SolverVariants WHERE fullName=? AND evaluation=?
                        """,
                    (solver, evaluationId),
                ):
                    solverVariantId = r[0]
                benchId = benchmarks.guess_benchmark_id(
                    connection, True, logic, family, str(benchmark)
                )
                if not benchId:
                    print(
                        f"WARNING: Benchmark {benchmark} of SMT-COMP {year} inc. not found"
                    )
                    continue
                with open(logfile, "r") as log:
                    count = 0
                    for line in log.readlines():
                        count = count + 1
                        ll = line.strip().split("\t")[1].strip()
                        status = benchmark_status(ll)
                        queryId = None
                        for r in connection.execute(
                            """
                                SELECT Id FROM Queries WHERE idx=? AND benchmark=?
                            """,
                            (count, benchId),
                        ):
                            queryId = r[0]
                        if not queryId:
                            break
                        connection.execute(
                            """
                            INSERT INTO Results(evaluation, query, solverVariant, status)
                            VALUES(?,?,?,?);
                            """,
                            (
                                evaluationId,
                                queryId,
                                solverVariantId,
                                status,
                            ),
                        )
                    connection.commit()
    connection.commit()
    return None


def add_smt_comp_inc_2024(connection, rawfolder):
    """
    Specialized routine for the incremental results of 2024.
    """
    name = f"SMT-COMP 2024"
    # TODO select SMT-COMP evaluation in full run.
    stats = make_stats_dict(name + "inc")
    for r in connection.execute(
        """
        SELECT Id FROM Evaluations WHERE name=?
        """,
        (name,),
    ):
        evaluationId = r[0]
    # modules.solvers.populate_evaluation_solvers(connection, name, evaluationId)

    print(f"Adding SMT-COMP 2024 incremental results")

    # Build mapping from scrambled file names to benchmark ids
    benchMap = {}
    with open("data/incremental/2024-mapping.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            scrambledFile = row["scrambled_file"].split(".")[0]
            originalFile = row["original_file"]
            benchmarkField = originalFile.split("/")
            logic = benchmarkField[1]
            benchmarkFamily = benchmarkField[2]
            benchmarkName = "/".join(benchmarkField[3:])

            benchId = benchmarks.guess_benchmark_id(
                connection, True, logic, benchmarkFamily, benchmarkName
            )
            if not benchId:
                print(
                    f"WARNING: Benchmark {benchmarkName} of SMT-COMP 2024 inc. not found"
                )
                continue
            benchMap[scrambledFile] = benchId

    path = Path(rawfolder) / "smtcomp_2024_data" / "incremental"
    for p in path.glob("*/*/*.logfiles.zip"):
        solver = p.parts[-2]
        solverVariantId = None
        for r in connection.execute(
            """
                SELECT Id FROM SolverVariants WHERE fullName=? AND evaluation=?
                """,
            (solver, evaluationId),
        ):
            solverVariantId = r[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                f"unzip '{p}'",
                cwd=tmpdir,
                shell=True,
                stdout=subprocess.DEVNULL,
            )
            for logfile in Path(tmpdir).glob("**/*yml.log"):
                try:
                    benchId = benchMap[logfile.name.split(".")[-3]]
                except KeyError:
                    continue
                with open(logfile, "r") as log:
                    sep = 0
                    count = 0
                    for line in log.readlines():
                        ll = line.strip()
                        if ll == "":
                            continue
                        if ll.startswith("---"):
                            sep = sep + 1
                        if sep >= 2:
                            count = count + 1
                            status = benchmark_status(ll)
                            for r in connection.execute(
                                """
                                    SELECT Id FROM Queries WHERE idx=? AND benchmark=?
                                    """,
                                (count, benchId),
                            ):
                                queryId = r[0]
                            connection.execute(
                                """
                                INSERT INTO Results(evaluation, query, solverVariant, status)
                                VALUES(?,?,?,?);
                                """,
                                (
                                    evaluationId,
                                    queryId,
                                    solverVariantId,
                                    status,
                                ),
                            )
                        # print(ll)

    connection.commit()
    return stats


def add_smt_comps(
    connection,
    smtcompwwwfolder,
    smtcompfolder,
    smtevalcsv,
    smtexecdb,
    smtcompraw,
    starexecinc,
    incremental=False,
):
    stats = []
    s = add_smt_comp_early(connection, "2005", "2005-07-12")
    stats.append(s)

    s = add_smt_comp_early(connection, "2006", "2006-08-21")
    stats.append(s)

    smtexecConnection = sqlite3.connect(smtexecdb)

    s = add_smtexec(
        connection, smtexecConnection, "2007", "2007-07-03", 20, 4, 30 * 60, 1.5
    )
    stats.append(s)

    s = add_smtexec(
        connection, smtexecConnection, "2008", "2008-07-07", 311, 4, 20 * 60, 1.5
    )
    stats.append(s)

    s = add_smtexec(connection, smtexecConnection, "2009", "2009-08-02", 529, 3)
    stats.append(s)

    s = add_smtexec(connection, smtexecConnection, "2010", "2010-07-15", 684, 3)
    stats.append(s)

    s = add_smtexec(
        connection, smtexecConnection, "2011", "2011-07-14", 856, 3, 20 * 60
    )
    stats.append(s)

    s = add_smtexec(
        connection, smtexecConnection, "2012", "2011-06-30", 1004, 3, 20 * 60
    )
    stats.append(s)

    smtexecConnection.close()

    s = add_smt_eval_2013(connection, smtevalcsv)
    stats.append(s)

    path2014 = smtcompfolder / "2014/csv/combined.tar.xz"
    s = add_smt_comp_2014(connection, path2014)
    stats.append(s)

    path2015 = smtcompfolder / "2015/csv/Main_Track.tar.xz"
    s = add_smt_comp_oldstyle(connection, path2015, "2015", "2015-07-02")
    stats.append(s)

    path2016 = smtcompfolder / "2016/csv/Main_Track.tar.xz"
    s = add_smt_comp_oldstyle(connection, path2016, "2016", "2016-07-02")
    stats.append(s)

    path2017 = smtcompfolder / "2017/csv/Main_Track.tar.xz"
    s = add_smt_comp_oldstyle(connection, path2017, "2017", "2017-07-23")
    stats.append(s)

    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2018", "2018-07-14")
    stats.append(s)

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2019", "2019-07-07")
    stats.append(s)

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2020", "2020-07-06")
    stats.append(s)

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2021", "2021-07-18")
    stats.append(s)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2022", "2022-08-10")
    stats.append(s)

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2023", "2023-07-06")
    stats.append(s)

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2024", "2024-07-22")
    stats.append(s)

    s = add_smt_comp_generic(connection, smtcompwwwfolder, "2025", "2025-08-11")
    stats.append(s)
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    if incremental:
        add_smt_comp_inc_starexec(connection, "2019", starexecinc)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        add_smt_comp_inc_starexec(connection, "2020", starexecinc)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        add_smt_comp_inc_starexec(connection, "2021", starexecinc)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        add_smt_comp_inc_starexec(connection, "2022", starexecinc)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        add_smt_comp_inc_starexec(connection, "2023", starexecinc)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        add_smt_comp_inc_2024(connection, smtcompraw)
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    for stat in stats:
        print_stats_dict(stat)


def add_eval_ratings(connection, evaluationId):
    """
    - for each logic
        - calculate n = |solvers that attempted at least one benchmark|
        - for each benchmark
                - calculate m = |solvers that solve that benchmark|
                - rating = 1 - m/n
    """
    count = 0
    for logicRow in connection.execute(
        """
        SELECT DISTINCT logic FROM Benchmarks
        """
    ):
        logic = logicRow[0]
        for logicSolversRow in connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) FROM Solvers AS s
                INNER JOIN SolverVariants AS sv ON sv.solver = s.id
                INNER JOIN Results AS r ON sv.id = r.solverVariant
                INNER JOIN Benchmarks AS b ON b.id = r.query
            WHERE b.logic=? AND r.evaluation=? AND b.isIncremental=0
            """,
            (logic, evaluationId),
        ):
            logicSolvers = logicSolversRow[0]
        if logicSolvers == 0:
            continue
        for queryRow in connection.execute(
            """
            SELECT DISTINCT(Queries.id) FROM Queries
            INNER JOIN Benchmarks on Queries.benchmark = Benchmarks.id
            INNER JOIN Results on Results.query=Queries.id
            WHERE logic=? AND isIncremental=0 AND Results.evaluation=?
            """,
            (
                logic,
                evaluationId,
            ),
        ):
            query = queryRow[0]
            for benchmarkSolversRow in connection.execute(
                """
                SELECT COUNT(DISTINCT s.id) FROM Solvers AS s
                    INNER JOIN SolverVariants AS sv ON sv.solver = s.id
                    INNER JOIN Results AS r ON sv.Id = r.solverVariant
                WHERE (r.status = 'unsat' OR r.status = 'sat')
                    AND r.query=? AND r.evaluation=?
                """,
                (query, evaluationId),
            ):
                benchmarkSolvers = benchmarkSolversRow[0]
            rating = 1 - benchmarkSolvers / logicSolvers
            connection.execute(
                """
                INSERT INTO Ratings(query, evaluation, rating, consideredSolvers, successfulSolvers)
                VALUES(?,?,?,?,?);
                """,
                (query, evaluationId, rating, logicSolvers, benchmarkSolvers),
            )
            count = count + 1
            if count % 1000 == 0:
                print(f"Inserted {count} ratings.")
            if count % 5000 == 0:
                connection.commit()
    connection.commit()


"""
Adds information derived from evaluations.
"""


def add_first_occurence(connection):
    connection.execute(
        """
        UPDATE Families AS fam SET firstOccurrence = (
            SELECT ev.date FROM Evaluations as ev
              INNER JOIN Results AS res ON res.evaluation = ev.id
              INNER JOIN Queries AS sb ON res.query = sb.id
              INNER JOIN Benchmarks AS bench ON bench.id = sb.benchmark
              WHERE bench.family = fam.id
            ORDER BY ev.date ASC
            LIMIT 1)
        """
    )


def add_inferred_status(connection):
    print(f"Add inferred sat status.")

    # There are odd disagreements with 2013, hence we exclude it
    name = "SMT Evaluation 2013"
    for r in connection.execute(
        """
        SELECT Id FROM Evaluations WHERE name=?
        """,
        (name,),
    ):
        evaluationId = r[0]

    # A benchmark gets a status if there is an evaluation where two different
    # solvers gave the same answer and there was no disagreement.
    connection.execute(
        """
        UPDATE Queries AS ss SET inferredStatus = "sat"
        WHERE ss.id IN (
            SELECT res1.query FROM Results AS res1
              INNER JOIN SolverVariants AS var1 ON var1.id = res1.solverVariant
              INNER JOIN Queries AS sub ON sub.id == res1.query
              WHERE res1.status == "sat"
                AND NOT res1.id == ?
                AND NOT EXISTS (
                        SELECT NULL
                        FROM Results AS res2
                        WHERE res1.query == res2.query
                          AND res1.evaluation == res2.evaluation
                          AND res2.status == "unsat"
                    )
                AND EXISTS (
                        SELECT NULL
                        FROM Results AS res2
                        INNER JOIN SolverVariants AS var2 ON var2.id = res2.solverVariant
                        WHERE res1.query == res2.query
                          AND var1.solver <> var2.solver
                          AND res1.evaluation == res2.evaluation
                          AND res2.status == "sat"
                    )
            GROUP BY res1.query
        )
        """,
        (evaluationId,),
    )
    connection.commit()
    print(f"Add inferred unsat status.")
    connection.execute(
        """
        UPDATE Queries AS ss SET inferredStatus = "unsat"
        WHERE ss.id IN (
            SELECT res1.query FROM Results AS res1
              INNER JOIN SolverVariants AS var1 ON var1.id = res1.solverVariant
              INNER JOIN Queries AS sub ON sub.id == res1.query
              WHERE res1.status == "unsat"
                AND NOT res1.id == ?
                AND NOT EXISTS (
                        SELECT NULL
                        FROM Results AS res2
                        WHERE res1.query == res2.query
                          AND res1.evaluation == res2.evaluation
                          AND res2.status == "sat"
                    )
                AND EXISTS (
                        SELECT NULL
                        FROM Results AS res2
                        INNER JOIN SolverVariants AS var2 ON var2.id = res2.solverVariant
                        WHERE res1.query == res2.query
                          AND var1.solver <> var2.solver
                          AND res1.evaluation == res2.evaluation
                          AND res2.status == "unsat"
                    )
            GROUP BY res1.query
        )
        """,
        (evaluationId,),
    )
    connection.commit()


def add_eval_summaries(connection):
    add_inferred_status(connection)
    for r in connection.execute(
        """
        SELECT id, name FROM Evaluations
        """
    ):
        print(f"Adding summaries for {r[1]}")
        evaluationId = r[0]
        add_eval_ratings(connection, evaluationId)
        connection.commit()
    print(f"Adding first occurrences of benchmark families (this will take a while)")
    add_first_occurence(connection)
    connection.commit()
