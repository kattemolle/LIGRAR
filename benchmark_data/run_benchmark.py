import line_graph_routing as lgr
import pickle

settings = []
for name in ['kagome', 'shuriken']:
    for side in range(1, 9, 2):
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

results = []
for setting in settings:
    try:
        result = lgr.benchmark(**setting)
        results.append(result)
        lgr.print_benchmark(result)
    except:
        print('Error occurred for', setting)

with open('benchmark_results.pkl', 'wb') as f:
    pickle.dump(results, f)
