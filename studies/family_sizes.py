#!/usr/bin/env python3

"""
    Histograms of the family size
"""

import argparse
import sqlite3
import matplotlib.pyplot as plt
import matplot2tikz
import numpy as np
import itertools
from matplotlib.patches import Rectangle
import numpy as np

number_of_bins = 20

parser = argparse.ArgumentParser()

parser.add_argument("database")

args = parser.parse_args()

connection = sqlite3.connect(args.database)

query = connection.execute(
    """
    SELECT l.logic, f.id, LOG10(COUNT(DISTINCT b.id)) AS benchmark_count
    FROM Logics l
    JOIN Benchmarks b ON b.logic = l.logic
    JOIN Families f ON f.id = b.family
    GROUP BY f.id
    ORDER BY l.logic ASC;
    """
)
result = query.fetchall()

logics = []
sizes = []
for logic, iter in itertools.groupby(result, lambda x: x[0]):
    fams = list(iter)
    if len(fams) > 5:
        logics.append(logic)
        sizes.append(list(map(lambda x: x[2], fams)))

maxSize = max(map(max, sizes))
minSize = min(map(min, sizes))
hist_range = (minSize, maxSize)
binned_data_sets = [
    np.histogram(d, range=hist_range, bins=number_of_bins)[0] for d in sizes
]
binned_maximums = np.max(binned_data_sets, axis=1)
# x_locations = np.arange(0, sum(binned_maximums), np.max(binned_maximums))
x_locations = np.arange(
    0, len(binned_data_sets) * np.max(binned_maximums), np.max(binned_maximums)
)
# The bin_edges are the same for all of the histograms
bin_edges = np.linspace(hist_range[0], hist_range[1], number_of_bins + 1)
heights = np.diff(bin_edges)
centers = bin_edges[:-1] + heights / 2

# Cycle through and plot each histogram
fig, ax = plt.subplots()
for x_loc, binned_data in zip(x_locations, binned_data_sets):
    lefts = x_loc - 0.5 * binned_data
    ax.barh(centers, binned_data, height=heights, left=lefts)

ax.set_xticks(x_locations, logics)

ax.set_ylabel("Numer of Benchmarks in Family (Base 10)")
ax.set_xlabel("Logic")

matplot2tikz.save("familyhistogram.tex")
plt.show()
