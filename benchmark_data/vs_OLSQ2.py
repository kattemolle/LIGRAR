#!/usr/bin/env python3
import sys

sys.path.insert(1, "../")
sys.path.insert(1, "../OLSQ2")

import line_graph_routing as lgr
import networkx as nx


kagome11 = nx.Graph(
    [
        (0, 1, {"color": 2}),
        (0, 6, {"color": 1}),
        (0, 3, {"color": 0}),
        (1, 3, {"color": 1}),
        (1, 7, {"color": 0}),
        (2, 5, {"color": 1}),
        (2, 4, {"color": 0}),
        (4, 5, {"color": 2}),
        (4, 7, {"color": 1}),
        (5, 6, {"color": 0}),
    ]
)

kagome22 = nx.Graph(
    [
        ((0, 0, 0), (0, 0, 1), {"color": 2}),
        ((0, 0, 0), (0, 0, 2), {"color": 0}),
        ((0, 0, 1), (0, 0, 2), {"color": 3}),
        ((0, 0, 1), (1, 0, 0), {"color": 1}),
        ((0, 0, 2), (0, 1, 0), {"color": 2}),
        ((1, 0, 0), (1, 0, 2), {"color": 0}),
        ((1, 0, 0), (1, 0, 1), {"color": 2}),
        ((1, 0, 2), (1, 1, 0), {"color": 2}),
        ((1, 0, 2), (0, 1, 1), {"color": 1}),
        ((1, 0, 2), (1, 0, 1), {"color": 3}),
        ((1, 1, 0), (0, 1, 1), {"color": 3}),
        ((1, 1, 0), (1, 1, 2), {"color": 1}),
        ((1, 1, 0), (1, 1, 1), {"color": 0}),
        ((0, 1, 0), (0, 1, 1), {"color": 0}),
        ((0, 1, 0), (0, 1, 2), {"color": 1}),
        ((0, 1, 1), (0, 1, 2), {"color": 2}),
        ((0, 1, 2), (0, 2, 0), {"color": 3}),
        ((1, 1, 2), (1, 2, 0), {"color": 3}),
        ((1, 1, 2), (0, 2, 1), {"color": 0}),
        ((1, 1, 2), (1, 1, 1), {"color": 2}),
        ((1, 2, 0), (0, 2, 1), {"color": 1}),
        ((1, 2, 0), (1, 2, 1), {"color": 2}),
        ((0, 2, 0), (0, 2, 1), {"color": 2}),
        ((1, 0, 1), (2, 0, 0), {"color": 1}),
        ((2, 0, 0), (2, 0, 2), {"color": 0}),
        ((2, 0, 2), (2, 1, 0), {"color": 2}),
        ((2, 0, 2), (1, 1, 1), {"color": 1}),
        ((2, 1, 0), (1, 1, 1), {"color": 3}),
        ((2, 1, 0), (2, 1, 2), {"color": 1}),
        ((2, 1, 2), (2, 2, 0), {"color": 3}),
        ((2, 1, 2), (1, 2, 1), {"color": 0}),
        ((2, 2, 0), (1, 2, 1), {"color": 1}),
    ]
)

kagome22 = nx.convert_node_labels_to_integers(kagome22)

kagome33 = nx.Graph(
    [
        (0, 1, {"color": 0}),
        (0, 11, {"color": 1}),
        (0, 21, {"color": 3}),
        (1, 30, {"color": 2}),
        (1, 33, {"color": 1}),
        (2, 3, {"color": 2}),
        (2, 29, {"color": 0}),
        (2, 28, {"color": 1}),
        (3, 15, {"color": 1}),
        (3, 28, {"color": 0}),
        (4, 5, {"color": 1}),
        (4, 38, {"color": 0}),
        (4, 13, {"color": 3}),
        (5, 13, {"color": 2}),
        (5, 39, {"color": 0}),
        (6, 7, {"color": 3}),
        (6, 25, {"color": 0}),
        (6, 35, {"color": 1}),
        (6, 23, {"color": 2}),
        (7, 11, {"color": 0}),
        (7, 23, {"color": 1}),
        (8, 9, {"color": 1}),
        (8, 27, {"color": 0}),
        (8, 34, {"color": 4}),
        (9, 31, {"color": 4}),
        (9, 32, {"color": 0}),
        (10, 20, {"color": 2}),
        (10, 24, {"color": 1}),
        (10, 37, {"color": 0}),
        (11, 21, {"color": 2}),
        (12, 13, {"color": 1}),
        (12, 14, {"color": 3}),
        (12, 26, {"color": 0}),
        (12, 17, {"color": 2}),
        (13, 17, {"color": 0}),
        (14, 24, {"color": 0}),
        (14, 25, {"color": 1}),
        (14, 26, {"color": 2}),
        (15, 16, {"color": 2}),
        (15, 20, {"color": 0}),
        (16, 19, {"color": 0}),
        (16, 20, {"color": 1}),
        (16, 26, {"color": 3}),
        (17, 18, {"color": 1}),
        (17, 34, {"color": 3}),
        (18, 35, {"color": 3}),
        (18, 36, {"color": 2}),
        (18, 34, {"color": 0}),
        (19, 26, {"color": 1}),
        (19, 29, {"color": 2}),
        (19, 38, {"color": 3}),
        (21, 36, {"color": 1}),
        (21, 31, {"color": 0}),
        (22, 23, {"color": 0}),
        (22, 37, {"color": 1}),
        (24, 25, {"color": 3}),
        (24, 37, {"color": 2}),
        (25, 35, {"color": 2}),
        (27, 34, {"color": 2}),
        (27, 39, {"color": 1}),
        (29, 38, {"color": 1}),
        (30, 33, {"color": 0}),
        (30, 32, {"color": 1}),
        (31, 32, {"color": 2}),
        (31, 36, {"color": 3}),
        (35, 36, {"color": 0}),
    ]
)
checkerboard = nx.Graph(
    [
        (0, 4, {"color": 0}),
        (0, 1, {"color": 1}),
        (0, 5, {"color": 2}),
        (1, 5, {"color": 3}),
        (1, 2, {"color": 0}),
        (1, 4, {"color": 2}),
        (2, 6, {"color": 3}),
        (2, 3, {"color": 2}),
        (2, 7, {"color": 1}),
        (3, 7, {"color": 0}),
        (3, 6, {"color": 1}),
        (4, 8, {"color": 3}),
        (4, 5, {"color": 1}),
        (5, 9, {"color": 5}),
        (5, 6, {"color": 4}),
        (5, 10, {"color": 0}),
        (6, 10, {"color": 5}),
        (6, 7, {"color": 2}),
        (6, 9, {"color": 0}),
        (7, 11, {"color": 3}),
        (8, 12, {"color": 0}),
        (8, 9, {"color": 1}),
        (8, 13, {"color": 2}),
        (9, 13, {"color": 3}),
        (9, 10, {"color": 4}),
        (9, 12, {"color": 2}),
        (10, 14, {"color": 3}),
        (10, 11, {"color": 1}),
        (10, 15, {"color": 2}),
        (11, 15, {"color": 0}),
        (11, 14, {"color": 2}),
        (12, 13, {"color": 1}),
        (13, 14, {"color": 0}),
        (14, 15, {"color": 1}),
    ]
)

# for p in range(1,7):
#     lgr.benchmark_against_OLSQ2(kagome11,p,obj_is_swap=True)

# lgr.benchmark_against_OLSQ2(kagome33, 1)
# lgr.benchmark_against_OLSQ2(kagome33, 2)
# lgr.benchmark_against_OLSQ2(checkerboard, 1)
lgr.benchmark_against_OLSQ2(checkerboard, 2)

# lgr.benchmark_against_OLSQ2(kagome22, 1)
# lgr.benchmark_against_OLSQ2(kagome22, 2)
# lgr.benchmark_against_OLSQ2(kagome22, 3)
# lgr.benchmark_against_OLSQ2(kagome22, 4)
