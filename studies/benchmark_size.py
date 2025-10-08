#!/usr/bin/env python3

"""
    Violin plots of the benchmark size
"""


import argparse
import sqlite3
import matplotlib.pyplot as plt
import matplot2tikz
import numpy as np
from matplotlib.patches import Rectangle

parser = argparse.ArgumentParser()

parser.add_argument("database")
parser.add_argument("--logic", default="ALL")

args = parser.parse_args()

if args.logic == "ALL":
    args.logic = "%"

connection = sqlite3.connect(args.database)

years = list(range(2005, 2025))
sizes = []
compressedSizes = []

for year in years:
    yearstr = f"{year}-12-31"
    oldyearstr = f"{year-1}-12-31"
    print(yearstr)
    query = connection.execute(
        """
        SELECT b.size, b.compressedSize FROM Benchmarks AS b
        JOIN Families AS fam ON fam.id = b.family
        WHERE b.logic LIKE ?
        AND fam.firstOccurrence <= ?
        AND fam.firstOccurrence > ?
        AND NOT b.isIncremental
        """,
        (args.logic, yearstr, oldyearstr),
    )
    result = query.fetchall()
    print(len(result))
    sizes.append(list(map(lambda x: x[0], result)))
    compressedSizes.append(list(map(lambda x: x[1], result)))

connection.close()
print("preparing plot")

# maxsizes = list(map(max, sizes))
# minsizes = list(map(min, sizes))

fig, ax = plt.subplots()
w = 0.75

# ax.violinplot(sizes, showmeans=False, showmedians=True)
bp = ax.boxplot(
    sizes,
    sym="",
    patch_artist=True,
    medianprops=dict(linewidth=1.5),
    capprops=dict(linewidth=1.5),
    boxprops=dict(facecolor="lightgray"),
    whis=(0, 100),
    widths=w,
)

side = "left"
y0, y1 = ax.get_ylim()

for i, box in enumerate(bp["boxes"]):
    x = i + 1  # box center at positions 1..N
    x0 = x - (w + 0.1) / 2 if side == "left" else x
    clip = Rectangle((x0, y0), (w + 0.1) / 2, y1 - y0, transform=ax.transData)

    box.set_clip_path(clip)
    bp["medians"][i].set_clip_path(clip)
    bp["caps"][2 * i].set_clip_path(clip)
    bp["caps"][2 * i + 1].set_clip_path(clip)

bp = ax.boxplot(
    compressedSizes,
    sym="",
    boxprops=dict(linestyle="--"),
    whiskerprops=dict(linestyle="--"),
    capprops=dict(linestyle="--"),
    medianprops=dict(linewidth=1.5),
    whis=(0, 100),
    widths=w,
)
side = "right"
for i, box in enumerate(bp["boxes"]):
    x = i + 1  # box center at positions 1..N
    x0 = x - (w + 0.1) / 2 if side == "left" else x
    clip = Rectangle((x0, y0), (w + 0.1) / 2, y1 - y0, transform=ax.transData)

    box.set_clip_path(clip)
    bp["medians"][i].set_clip_path(clip)
    bp["caps"][2 * i].set_clip_path(clip)
    bp["caps"][2 * i + 1].set_clip_path(clip)

# ax.step(range(1,21), maxsizes)
# ax.step(range(1,21), minsizes)

plt.yscale("log", base=2)
ax.set_ylabel("Size (Bytes)")
ax.set_xlabel("Year (2005-2024)")
ax.grid(True)

matplot2tikz.save("sizeplot.tex")
plt.show()
# plt.clf()
# plt.close()
