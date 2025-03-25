# Tooling to Build a Database of SMT-LIB Problems

This repository contains Python scripts that can be used to build a database
from a folder that contains a copy of the SMT-LIB benchmark library.  Such a
database can than be used to quickly select benchmarks for experiments, or to
study the benchmark library itself.

The database will also store results large-scale evaluations, such as 
SMT-COMP.  This will allow us to track benchmark difficulty over time.

## Webapp

There is a simple webapp to view benchmark data.  It can best started
locally using Docker.

To run the Docker container first execute
> docker build -t smtlib-db .
to build the Docker image.
To start the image run:
> docker run --rm -it -p 8000:5000 --name smtlib-db-container smtlib-db
Afterwards the webapp should be available at "http://localhost:8000".

## Database Scheme

The scheme is not yet fixed, and can evolve as we implement features.
The SMT-LIB folder structure follows the scheme `[LOGIC]/[DATE]-[BENCHMARKSET]/[FILENAME]`.

```sql
-- One row for each benchmark file.
CREATE TABLE Benchmarks(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL, -- File path after the family (not unique)
        family INT, -- Reference to the family of the benchmark
        logic NVARCHAR(100) NOT NULL, -- Logic string
        isIncremental BOOL, -- True if benchmark is in incremental folder
        size INT, -- Size of the benchmark file in bytes
        compressedSize INT, -- Size in bytes after compression with zstd
        license INT, -- Reference to license of the benchmark
        generatedOn DATETTIME, -- 'Generated on' field of the :source header.
        generatedBy TEXT, -- 'Generated by' field of the :source header.
        generator TEXT, -- 'Generator' field of the :source header.
        application TEXT, -- 'Application' field of the :source header.
        description TEXT, -- Text of the :source header after standard fields.
        category TEXT, -- Either 'industrial', 'crafted', or 'random'.
        passesDolmen BOOL, -- The Dolmen checker reports no error.
        passesDolmenStrict BOOL, -- Dolmen with '--strict=true' reports no error.
        queryCount INT NOT NULL, -- Number of (check-sat) calls in the benchmark.
        FOREIGN KEY(family) REFERENCES Families(id)
        FOREIGN KEY(license) REFERENCES Licenses(id)
        FOREIGN KEY(logic) REFERENCES Logics(logic)
    );
-- One row for each (check-sat) call in a benchmark.
CREATE TABLE Queries(
        id INTEGER PRIMARY KEY,
        benchmark INT, -- Reference to the benchmark this query belongs to.
        index INT, -- Index of the query in the benchmark.  Counted from 1.
        normalizedSize INT, -- Size in bytes of the query.
        compressedSize INT, -- Size in bytes of the query compressed with zstd.
        assertsCount INT, -- Number of asserts in the query.
        -- Number of `declare-fun` commands that declare function with at
        -- least one argument.  Otherwise, these `declare-fun` commands are
        -- counted as constants.
        declareFunCount INT,
        -- Number of `declare-const` and 0-ary `declare-fun`.
        declareConstCount INT,
        declareSortCount INT, -- Num. of `declare-sort` commands.
        -- Number of `define-fun` commands that expect at least one argument.
        -- Otherwise, these are counted as `constantFunCount`.
        defineFunCount INT,
        -- Number of recursive functions.  That is, functions introduced by
        -- `define-fun-rec` or `define-funs-rec`.  Each function in
        -- `define-funs-rec` is counted individually.
        defineFunRecCount INT,
        constantFunCount INT, -- Num. of 0-ary `define-fun` (i.e., constants).
        defineSortCount INT, -- Num. of `define-sort` commands.
        -- Number of datatypes.  That is, datatypes introduced by
        -- `declare-datatype` or `declare-datatypes`.  Each datatype in
        -- `declare-datatypes` is counted individually.
        declareDatatypeCount INT,
        -- Maximum of "open parenthesis" of any term in this query.
        -- For example, `(a (b (c d) (e (f g))))` has a term depth of 4.
        -- See the description of `symbolCounts` for the lists of terms
        -- considere.
        maxTermDepth INT,
        status TEXT, -- Status of the query as declared in the benchmark.
        inferredStatus TEXT,  -- Status derived from evaluation results.
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    );
-- Represents a family of benchmarks.  Usually, all benchmarks in a family are
-- submitted together.  A family can contain benchmarks from different logics,
-- and even incremental and non-incremental benchmarks.
CREATE TABLE Families(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL, -- Name of the family.
        folderName TEXT NOT NULL, -- Full name of the folder, including the date.
        -- Family date according to folder name.  If only a year is given, the
        -- date is the first of January of that year.
        date DATE,
        -- Date of the first evaluation where any benchmark of this family was
        -- used.
        firstOccurrence DATE,
        benchmarkCount INT NOT NULL, -- Number of benchmarks in the family.
        UNIQUE(folderName)
    );
-- A solver listed as a target solver in the bechnmark header.
CREATE TABLE TargetSolvers(
        id INTEGER PRIMARY KEY,
        benchmark INTEGER NOT NULL, -- Benchmark with this solver as a target.
        solverVariant INT NOT NULL, -- Solver variant given by the benchmark.
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id),
        FOREIGN KEY(solverVariant) REFERENCES SolverVariants(id)
    );
CREATE TABLE Licenses(
        id INTEGER PRIMARY KEY,
        name TEXT, -- Name used for the license in the benchmarks
        link TEXT, -- Link to webpage of the license
        spdxIdentifier TEXT -- License identifier see https://spdx.org/licenses/
    );
-- One entry for each logic string currently in use.
CREATE TABLE Logics(
        logic TEXT PRIMARY KEY,  -- Logic string
        -- Theories and features activated by the logic.
        quantifierFree BOOL,
        arrays BOOL,
        uninterpretedFunctions BOOL,
        bitvectors BOOL,
        floatingPoint BOOL,
        dataTypes BOOL,
        strings BOOL,
        nonLinear BOOL, -- If false, only linear arithmetic is allowed.
        difference BOOL, -- If true, only difference logic is allowed.
        reals BOOL,
        integers BOOL
    );
-- This tables list symbols that we count.  Most of them are predefined
-- operators, but we also count quantifiers (eg. `forall`).
CREATE TABLE Symbols(
        id INT PRIMARY KEY,
        name TEXT
    );
-- The number of occurences of that symbol.
-- We count occurences in: assert, define-fun, define-fun-rec, define-funs-rec,
-- and declare-datatype.
CREATE TABLE SymbolCounts(
        symbol INT,
        query INT,
        count INT NOT NULL,
        FOREIGN KEY(symbol) REFERENCES Symbols(id)
        FOREIGN KEY(query) REFERENCES Queries (id)
    );
-- List of solvers that participated in the competition or are mentioned as
-- target solver.  Solvers based on other solvers (such as the Z3-based string
-- solvers are listed as their own entries.
CREATE TABLE Solvers(
        id INTEGER PRIMARY KEY,
        name TEXT,
        link TEXT -- Link to solver webpage, or publication if no webpage exists.
    );
-- Since solvers use different versioning schemes, there is
-- no proper version table.  Instead there is only one tables
-- that can be used both for versions, and multiple variants
-- submited to the same competition.
CREATE TABLE SolverVariants(
        id INTEGER PRIMARY KEY,
        fullName TEXT, -- Full string that was used to refer to the variant.
        solver INT,
        -- The evaluation that used that variant.  NULL for variants that are
        -- target solvers of benchmarks.
        evaluation INT,
        FOREIGN KEY(solver) REFERENCES Solvers(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
    );
-- This table lists evaluations.  These are usually, but not necessary, SMT
-- competitions.
CREATE TABLE Evaluations(
        id INTEGER PRIMARY KEY,
        name TEXT,
        date DATE, -- Date when results were published. Usually, the SMT workshop.
        link TEXT
    );
-- This table maps queries to solver variants and results.
-- Both cpu time and wallclock time can be NULL if they are not known. Time is
-- in seconds.
CREATE TABLE Results(
        id INTEGER PRIMARY KEY,
        evaluation INTEGER,
        query INT,
        solverVariant INT,
        cpuTime REAL,
        wallclockTime REAL,
        status TEXT, -- sat, unsat, or unknown.  Might disagree with known status.
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        FOREIGN KEY(query) REFERENCES Queries(id)
        FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
   );
-- Dificulty ratings (see below)
CREATE TABLE Ratings(
        id INTEGER PRIMARY KEY,
        query INT,
        evaluation INT, 
        rating REAL, -- 1 - m/n
        consideredSolvers INT, -- n
        successfulSolvers INT, -- m
        FOREIGN KEY(query) REFERENCES Queries(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
   );
```

Benchmark difficulty ratings are calculated for each evaluation.  This
calculation first counts the number $n$ of solvers that attempted at least one
benchmark in the logic of the benchmark.  Then it count the number $m$ of
solvers that solved the benchmark.  The rating is $1 - m/n$.
A solver solves a benchmark if any of its variant gives an answer that doesn't
disagree with the query status or the inferred query status.

Note that ratings with few considered solvers (e.g., < 3) are unreliable.

## Scripts

* `prepopulate.py` sets up the database file and inserts static data.
* `addbenchmark.py` adds a benchmark to the database file.
* `postprocess.py` adds evaluations, and performs any other operation that
  requires all benchmarks to be in the database.

## TODO

* Support for incremental benchmarks.
