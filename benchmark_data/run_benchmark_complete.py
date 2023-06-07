import line_graph_routing as lgr
import pickle

settings = []
for name in ['complete']:
    for side in range(3, 10, 2):
        for p in [side*100]:
            for optimization_level in range(2):
                setting = {'name': name,
                           'size': side,
                           'circuit_type': 'random',
                           'p': p,
                           'repetitions': 16,
                           'optimization_level': optimization_level,
                           'methods': ['sabre']
                           }
                settings.append(setting)

results = []
for setting in settings:
    result = lgr.benchmark(**setting)
    results.append(result)
    lgr.print_benchmark(result)

with open('benchmark_results_complete.pkl', 'wb') as f:
    pickle.dump(results, f)
