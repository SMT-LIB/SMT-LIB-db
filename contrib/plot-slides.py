#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np

data = np.array([
    [5, 3151  , 0     , 0],
    [6, 33987 , 354   , 338],
    [7, 47939 , 1270  , 1239],
    [8, 52326 , 2723  , 2667],
    [9, 85151 , 4628  , 4507],
    [10, 86683 , 6998  , 6532],
    [11, 94744 , 8738  , 8146],
    [12, 94744 , 10802 , 10246],
    [13, 95454 , 10802 , 10246],
    [14, 126054, 95391 , 93761],
    [15, 174569, 117958, 116208],
    [16, 174571, 153100, 151676],
    [17, 256420, 153267, 151966],
    [18, 301303, 238387, 221866],
    [19, 319497, 301303, 285614],
    [20, 377910, 310431, 293814],
    [21, 383409, 336696, 318856],
    [22, 393089, 357509, 337988],
    [23, 435937, 373195, 353225],
    [24, 445071, 405606, 383394]])

fig, ax = plt.subplots()

ax.grid(axis='y')
ax.bar(data[0:, 0],data[0:, 1], color='#918b3b',edgecolor='black', hatch='///') # total
ax.bar(data[0:, 0],data[0:, 2], color='#159393',edgecolor='black', hatch='xxx') # fresh
ax.bar(data[0:, 0],data[0:, 3], color='#695d69',edgecolor='black', hatch='...') # solved
ax.set_xlim(left=4.5, right=24.5)
ax.set_xticks(data[0:, 0])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['left'].set_visible(False)

plt.savefig('visplt.pdf',bbox_inches='tight')
#plt.show()

