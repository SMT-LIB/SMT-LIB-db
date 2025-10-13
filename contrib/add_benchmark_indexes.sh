#!/usr/bin/env bash

echo "Adding indexes after adding benchmarks"
echo "    on file" "$1"

echo "Add index for Benchmarks table"
sqlite3 "$1" "create index benchIdx1 on Benchmarks(name, family, logic, isIncremental);"

echo "Add index for Queries table"
sqlite3 "$1" "create index benchIdx2 on Queries(benchmark, idx);"

echo "Add index for Families table"
sqlite3 "$1" "create index benchIdx3 on Families(name, folderName, firstOccurrence);"

echo "Call SQLite analyze."
sqlite3 "$1" "analyze;"
