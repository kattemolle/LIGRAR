import line_graph_routing as lgr
import pickle

settings = []
for name in ["kagome", "shuriken"]:
    for p in [1]:
        for optimization_level in [1]:
            setting = {
                "name": name,
                "size": (1, 3),
                "circuit_type": "quantum_simulation",
                "p": p,
                "repetitions": 4,
                "optimization_level": optimization_level,
                "methods": ["basic", "lookahead", "sabre", "stochastic"],
            }
            settings.append(setting)

results = []
for setting in settings:
    result = lgr.benchmark(**setting)
    results.append(result)
    lgr.print_benchmark(result)

with open("benchmark_results_other_methods.pkl", "wb") as f:
    pickle.dump(results, f)

with open("benchmark_results_other_methods.pkl", "rb") as f:
    results = pickle.load(f)

for result in results:
    lgr.print_benchmark(result)
