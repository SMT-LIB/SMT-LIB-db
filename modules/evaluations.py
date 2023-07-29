import tempfile
import subprocess
import csv
import benchmarks

def setup_evaluations(connection):
    connection.execute(
        """CREATE TABLE Evaluations(
        id INTEGER PRIMARY KEY,
        name TEXT,
        date DATE,
        link TEXT,
        );"""
    )
    # TODO: add/move result table here

def add_smt_comp_2022(connection, folder):
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            f"tar xvf {folder}/2022/results/raw-results.tar.xz -C {tmpdir}",
            shell=True,
        )
        with open(f"{tmpdir}/raw-results-sq.csv", newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                # remove the 'track_single_query/' from the start
                fullbench = row['benchmark'][19:]
                try:
                    benchmarkId = benchmarks.get_benchmark_id(fullbench, isIncremental=False)
                except NameError:
                    print("WARNING: Benchmark {fullbench} of SMT-COMP 2022 not found")
                    continue

                # remove "-wrapped" from the end
                solver = row['solver'][:-8]

                # 'benchmark' track_single_query/LOGIC/
                # 'solver' with -wrapped
                # cpu time wallclock time unit? seconds most likely
                # result   expected  "starexec-unknown"
                # check if solver variant is known, if not
                #    Run a "guess solver" routine", if failure print error with info
                #    Create variant
                # Write to database

                print(', '.join(row))
        # TODO: csv parser to add every line, map to solvers


def add_smt_comps(connection, folder):
    add_smt_comp_2022(connection, folder)
