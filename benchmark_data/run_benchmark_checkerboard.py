import line_graph_routing as lgr  # Loading these makes these cells stand-alone
import pickle

settings = []
for name in ['checkerboard']:
    for side in [i+0.5 for i in range(1, 9, 2)]:
        for p in [1, 8, 16]:
            for optimization_level in range(4):
                setting = {'name': name,
                           'size': (side, side),
                           'circuit_type': 'quantum_simulation',
                           'p': p,
                           'repetitions': 16,
                           'optimization_level': optimization_level,
                           'methods': ['sabre']
                           }
                settings.append(setting)

# Unocmment to rerun benchmarks. This takes a couple of hours.
results = []
for setting in settings:
    result = lgr.benchmark(**setting)
    results.append(result)
    lgr.print_benchmark(result)

with open('benchmark_results_checkerboard.pkl', 'wb') as f:
    pickle.dump(results, f)
