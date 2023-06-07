"""
Code to implement line-graph routing. For explaination of the code, see line_graph_routing.ipynb or line_graph_routing.py
"""

import networkx as nx
from netket.graph import Kagome
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.converters import circuit_to_dag, dag_to_circuit
from collections import OrderedDict
from matplotlib import pyplot as plt
import numpy as np
import random as rand
import qiskit.circuit as qkcirc
from qiskit.transpiler import TransformationPass, CouplingMap
from qiskit.compiler import transpile
from qiskit.dagcircuit import dagnode
from time import time
from tabulate import tabulate
from scipy.stats import bootstrap


class DoubleSwapRemover(TransformationPass):
    """
    Transpiler pass to cancel double swap gates.
    """

    def run(self, dag):
        for node in dag.op_nodes():
            if node.op.name == 'swap':
                children = list(dag.successors(node))
                if len(children) == 1 and children[0].op.name == 'swap':
                    replacement = QuantumCircuit(2)
                    dag.substitute_node_with_dag(
                        node, circuit_to_dag(replacement))
                    dag.substitute_node_with_dag(
                        children[0], circuit_to_dag(replacement))
        return dag


class OuterSwapRemover(TransformationPass):
    """
    Transpiler pass to remove superflous swap gates at the beginning and end of the circuit.
    Warning: no relabeling of the qubits is performed.
    """

    def run(self, dag):
        for node in dag.op_nodes():
            if node.op.name == 'swap':
                parents = dag.predecessors(node)
                children = dag.successors(node)
                init_swap = all(
                    type(parent) == dagnode.DAGInNode for parent in parents)
                post_swap = all(
                    type(child) == dagnode.DAGOutNode for child in children)
                if init_swap or post_swap:
                    replacement = QuantumCircuit(2)
                    dag.substitute_node_with_dag(
                        node, circuit_to_dag(replacement))

        return dag


def coupling_graph(qc: QuantumCircuit) -> nx.Graph:
    """
    Return the coupling graph of a qiskit QuantumCircuit. All gate labels of qc must be ints. The lowest qubit label must be 0. Circuits must consist out of one- and two-qubit gates by assumption.
    """
    cg = nx.Graph()

    for inst in qc.data:
        qubits = inst.qubits
        assert len(qubits) == 1 or len(
            qubits) == 2, 'coupling_graph() is currently only implemented for circuits consisting out if one- and two-qubit gates.'
        if len(qubits) == 1:
            q = qc.find_bit(qubits[0]).index
            assert type(q) == int
            cg.add_node(q)
        elif len(qubits) == 2:
            q0 = qc.find_bit(qubits[0]).index
            q1 = qc.find_bit(qubits[1]).index
            assert type(q0) == int and type(q1) == int
            cg.add_edge(q0, q1)

    assert(sorted(cg.nodes)[0] == 0), 'Lowest node int must be 0.'
    return cg


def remove_idle_qwires(qc):
    # Return a QuantumCirucuit with idle qubits removed from qc. Does not resize the QuantumRegister of the qubits.
    dag = circuit_to_dag(qc)
    idle_wires = list(dag.idle_wires())
    for w in idle_wires:
        dag._remove_idle_wire(w)
        dag.qubits.remove(w)

    dag.qregs = OrderedDict()

    return dag_to_circuit(dag)


def line_graph_route(qc: QuantumCircuit) -> QuantumCircuit:
    """
    Reroute the gates of qiskit.Quantum circuit c by line-graph rerouting. Return the rerouted circtuit cp.
    """
    def heavy(g):
        # Return the heavy variant h of the networkx.Graph g, assuming g  is of the form as returned by Roussopouloss algorithm (nx.inverse_line_graph). The newly added 'heavy' nodes have labels equal to the graph that was put in to Roussopoulos' algorithm. This is algorithm 1 in the paper.
        h = nx.Graph()
        for a, b in g.edges():
            cn = tuple(set(a) & set(b))  # common node
            assert len(cn) == 1
            if len(a) == 1 and len(b) != 1:
                b = str(b)
                h.add_edge(a[0], b)
            elif len(a) != 1 and len(b) == 1:
                a = str(a)
                h.add_edge(a, b[0])
            if len(a) != 1 and len(b) != 1:
                a = str(a)
                b = str(b)
                h.add_edge(a, cn[0])
                h.add_edge(cn[0], b)

        return h

    def lone_leaf(g, node):
        # Return true if `node` is a node of degree one in networkx.graph `g` and the neighbor of `node` is not connected to any other nodes of degree one. This function is needed for 'augmented line-graph routing' which reduces the number qubits.
        assert g.has_node(node)
        if g.degree[node] != 1:
            return False
        else:
            # The single neighbour of `node`.
            nbr = list(nx.neighbors(g, node))[0]
            # Siblings of `node`. Contains `node` itself.
            sibs = list(nx.neighbors(g, nbr))
            # list of siblings with degree one
            lone_sibs = [sib for sib in sibs if g.degree[sib] == 1]
            assert len(lone_sibs) >= 1
            if len(lone_sibs) == 1:
                return True
            else:
                return False

    def nodes_to_ints(h):
        # Return h with all non-int nodes mapped to ints. Int nodes remain unchanged.
        ints = [i for i in h.nodes if type(i) == int]
        maxint = max(ints)
        mapping = {}
        i = 1
        for node in h.nodes():
            if type(node) != int:
                mapping[node] = maxint+i
                i += 1
        h = nx.relabel_nodes(h, mapping)
        return h

    def resize_register_to(qc, h):
        # Resize the quantum register of QuantumCircuit qc to the size of the number of nodes of h. All nodes of h must be ints.
        qcp = QuantumCircuit(max(h.nodes)+1)
        for qcinst in qc.data:
            qubits = (qc.find_bit(qubit).index for qubit in qcinst.qubits)
            qcp.append(qcinst.replace(qubits=qubits))
        return qcp

    def bare_reroute(qc, h):
        # Line-graph reroute without removal of lone leaf qubits. And without removal of superflous SWAPs. Map circuit on cg, the coupling graph of qc, to a circuit on heavy(g), with g=L^-1(cg).
        cp = QuantumCircuit(max(h.nodes)+1)
        for inst in qc.data:
            qubits = inst.qubits
            assert len(qubits) == 1 or len(
                qubits) == 2, 'line_graph_route() is currently only for circuits consisting out if one- and two-qubit gates.'
            if len(inst.qubits) == 1:
                cp.append(inst)
            elif len(qubits) == 2:
                i = qc.find_bit(qubits[0]).index
                j = qc.find_bit(qubits[1]).index
                path = nx.shortest_path(h, source=i, target=j)
                assert len(
                    path) == 3, 'The path through h=heavy(g) from node i to j of g must touch 3 nodes.'
                m = path[1]
                if inst.operation.name != 'pad':
                    # Always 'swap in' the qubit with the lowest degree.
                    if h.degree[i] >= h.degree[j]:
                        cp.swap(j, m)
                        cp.append(inst.replace(qubits=(i, m)))
                        cp.swap(m, j)
                    else:
                        cp.swap(i, m)
                        cp.append(inst.replace(qubits=(m, j)))
                        cp.swap(m, i)

        return cp

    def remove_lone_leaf(qc, h):
        # Return circuit with lone leaf qubits removed accoring to 'agumented line-graph routing'.
        cp = QuantumCircuit(qc.num_qubits)

        for inst in qc.data:
            qubits = inst.qubits
            if len(qubits) == 1:
                i = qc.find_bit(qubits[0]).index
                if lone_leaf(h, i):
                    nbr = list(nx.neighbors(h, i))[0]
                    cp.append(inst.replace(qubits=(nbr,)))
                else:
                    cp.append(inst)
            elif len(qubits) == 2:
                i = qc.find_bit(qubits[0]).index
                j = qc.find_bit(qubits[1]).index
                if lone_leaf(h, i) or lone_leaf(h, j):
                    assert inst.operation.name == 'swap' or inst.operation.name == 'pad_swap', 'In the rerouted circuit (pre removal of degree 1 nodes) any two-qubit gate hitting a lone leaf node must be a SWAP gate.'
                    # This SWAP is **not** included in cp, which removes the need for the dangling qubit.
                else:
                    cp.append(inst)
            else:
                raise ValueError(
                    'A non- one- or two-qubit gate was encountered during routing.')

        return cp

    def fix_labels(qc, h):
        # Fix labels of qubits that were before lone leaf so that the old labeling of nodes is retained in the output circuit. This is not essential, but is practical when gates need to be added to the circuit *after* routing.
        swap_dict = {}
        for node in h.nodes:
            if lone_leaf(h, node):
                nbr = list(nx.neighbors(h, node))
                assert len(nbr) == 1
                nbr = nbr[0]
                swap_dict[nbr] = node

        cp = QuantumCircuit(qc.num_qubits)
        for inst in qc.data:
            qubits = inst.qubits
            i = qc.find_bit(qubits[0]).index
            if len(qubits) == 2:
                j = qc.find_bit(qubits[1]).index
            if len(qubits) == 1 and i in swap_dict:
                node = swap_dict[i]
                cp.append(inst.replace(qubits=(node,)))
            elif len(qubits) == 2 and i in swap_dict and j not in swap_dict:
                node = swap_dict[i]
                cp.append(inst.replace(qubits=(node, j)))
            elif len(qubits) == 2 and j in swap_dict and i not in swap_dict:
                node = swap_dict[j]
                cp.append(inst.replace(qubits=(i, node)))
            elif len(qubits) == 2 and i in swap_dict and j in swap_dict:
                node0 = swap_dict[i]
                node1 = swap_dict[j]
                cp.append(inst.replace(qubits=(node0, node1)))
            else:
                cp.append(inst)

        return cp

    # Apply line-graph routing.
    cg = coupling_graph(qc)
    assert nx.is_connected(
        cg), 'Line-graph routing only implemented for connected connectivity graphs. Route the disconnected circuits seperately or add padding identity gates with pad_gate()'
    g = nx.inverse_line_graph(cg)
    h = heavy(g)
    assert nx.is_connected(h)
    h = nodes_to_ints(h)
    qc = resize_register_to(qc, h)
    start = time()
    qc = bare_reroute(qc, h)
    qc = remove_lone_leaf(qc, h)
    qc = fix_labels(qc, h)
    qc = DoubleSwapRemover()(qc)
    qc = OuterSwapRemover()(qc)
    end = time()
    qc = remove_idle_qwires(qc)

    return qc


# The folowing runctions are for demonstration.


def kagome(n: int, m: int) -> nx.Graph:
    """
    Return the kagome graph of n by m unit cells, with 'padded' edges.
    """
    n += 1
    m += 1
    lat = Kagome(extent=[n, m], pbc=False)
    g = nx.Graph()
    g.add_edges_from(lat.edges())
    g.remove_nodes_from(range(0, 3*m*n, 3*m))
    g.remove_nodes_from(range(1, 3*m, 3))
    g = nx.convert_node_labels_to_integers(g)
    return g


def shuriken(n: int, m: int) -> nx.Graph:
    """
    Return shuriken graph of n by m shurikens with open boundary conditions.
    """
    shuriken = [(0, 1), (1, 2), (1, 3), (2, 3), (3, 4), (3, 5),
                (4, 5), (5, 6), (5, 7), (6, 7), (7, 0), (7, 1)]
    shuriken = nx.Graph(shuriken)

    def new_shuriken(shuriken):
        mapping = {i: i+8 for i in shuriken.nodes}
        ns = nx.relabel_nodes(shuriken, mapping)
        return ns

    def shuriken_column(n):
        ns = shuriken  # New shuriken
        col = shuriken.copy()  # One col of shuriken lattice
        for row in range(1, n):
            ns = new_shuriken(ns)
            col.add_edges_from(ns.edges)
            ln = (row-1)*8+6  # lower node of upper shuriken
            un = row*8+2  # Upper node of lower shuriken
            col = nx.contracted_nodes(col, ln, un)

        return col

    def append_column(n, cols, newcol):
        i_max = max(cols.nodes)
        mapping = {i: i+i_max+1 for i in newcol.nodes}
        newcol = nx.relabel_nodes(newcol, mapping)
        j_max = max(newcol.nodes)
        cols.add_edges_from(newcol.edges)
        mergers = [[(i_max-3)-i*8, j_max-7-i*8] for i in range(n)]
        for merger in mergers:
            cols = nx.contracted_nodes(cols, *merger)

        return cols

    cols = shuriken_column(n)
    for colind in range(1, m):
        newcol = shuriken_column(n)
        cols = append_column(n, cols, newcol)

    cols = nx.convert_node_labels_to_integers(cols)
    return cols


def checkerboard(n: int, m: int) -> nx.Graph:
    """
    Return checkerbord graph of 2n by 2m unit cells, with open boundary conditions and padded edges.
    """
    n = int(n*2 +
            1)  # Go from size specification by unit cells to specification by nodes.
    m = int(m*2+1)
    cb = nx.grid_2d_graph(n, m)
    for i in range(0, n-1, 2):
        for j in range(0, m-1, 2):
            cb.add_edge((i, j), (i+1, j+1))
            cb.add_edge((i+1, j), (i, j+1))
    for i in range(1, n-1, 2):
        for j in range(1, m-1, 2):
            cb.add_edge((i, j), (i+1, j+1))
            cb.add_edge((i+1, j), (i, j+1))

    cb = nx.convert_node_labels_to_integers(cb)
    return cb


def random_line_graph(n: int) -> nx.Graph:
    """
    Create an Erdos-Renyi graph on n nodes and return its line graph.
    """
    g = nx.erdos_renyi_graph(n, 2/3)  # Connected with high probability
    while not nx.is_connected(g):
        g = nx.erdos_renyi_graph(n, 2*np.log(n)/n)
    l = nx.line_graph(g)
    l = nx.convert_node_labels_to_integers(l)
    return l


def random_circuit(g, m):
    """
    Return a qiskit quantum circuit with with connectivity graph g and m random 2-qubit Clifford + T gates.
    """
    if not all(type(node) == int for node in g.nodes):
        print("warning: converting all nodes to integers")
        g = nx.convert_node_labels_to_integers(g)
    edges = list(g.edges)
    n = len(g.nodes)
    # List of gates to choose from. Make the prob. of choosing CNOT higher because these are the interesting gates in a routing problem.
    gates = [qkcirc.library.CXGate()]*2+[qkcirc.library.HGate(),
                                         qkcirc.library.SGate(), qkcirc.library.TGate()]

    def append_random_instruction_to(qc):
        gate = rand.choice(gates)
        qint = rand.randint(0, n-1)
        if gate.num_qubits == 1:
            q = rand.randint(0, n-1)
            qc.append(gate, (q,))
        elif gate.num_qubits == 2:
            qs = rand.choice(edges)
            qc.append(gate, qs)

    qc = QuantumCircuit(n)

    for _ in range(m):
        append_random_instruction_to(qc)

    return qc


def pad_gate() -> QuantumCircuit:
    """
    The current implementation of line-graph routing assumes circuits with connected connectiviy graphs. The pad gate can be added to a circuit with a disconnected connectivity graph to make it connected.
    """
    qc = QuantumCircuit(2, name='pad')
    return qc


def prepare_singlet() -> QuantumCircuit:
    """
    Return qiskit circuit that prepares the two-qubit singlet state.
    """
    qc = QuantumCircuit(2, name='singlet')
    qc.h(0)
    qc.z(0)
    qc.x(1)
    qc.cnot(0, 1)
    return qc


def heis_gate(alpha: Parameter) -> QuantumCircuit:
    """
    Return HEIS gate as qiskit circuit with qiskit.circuit.Parameter alpha
    """
    qc = QuantumCircuit(2, name='heis')
    qc.sx(1)
    qc.rz(-np.pi, 0)
    qc.sx(0)
    qc.rz(-np.pi/2, 0)
    qc.cnot(0, 1)
    qc.rx(np.pi/2, 0)
    qc.rz(-alpha/2, 1)
    qc.rz(np.pi/2+alpha/2, 0)
    qc.cnot(0, 1)
    qc.rx(np.pi/2, 0)
    qc.rz(alpha/2, 1)
    qc.cnot(0, 1)
    qc.x(0)
    qc.x(1)
    qc.rz(-np.pi/2, 0)
    return qc


def edge_coloring(g: nx.Graph, verbose=True) -> nx.Graph:
    """
    Return an edge coloring of the networkx.Graph g as a networkx.Graph with 'color' edge attributes. Color 0 forms a perfect
    matching. If such a perfect matching was not found (which does not mean it does not exist) an assertion error is raised.
    Color 0 forms a perfect matching for many patches, including those of m x m unit cells, with m odd and arbitrarily large.
    Does not return a perfect matching for all patches, for example patches with m x m unit cells with m even.
    """
    line = nx.line_graph(g)
    # To obtain an _edge_ coloring of g, we use the fact that a vertex coloring of the line graph of g is equivalent to an edge coloring of g.
    coloring = nx.greedy_color(line, strategy='independent_set')
    nx.set_edge_attributes(g, coloring, 'color')
    matching = {edge[:2]
                for edge in g.edges(data=True) if edge[2]['color'] == 0}
    if nx.is_perfect_matching(g, matching):
        if verbose == True:
            print('Matching is perfect')
    else:
        raise Exception(
            'No perfect matching found, try another method for coloring the graph.')

    colors = [g[u][v]['color'] for u, v in g.edges]
    if max(colors) == 3:  # Specific to kagome lattice
        if verbose == True:
            print('Edge coloring is minimal')
    else:
        if verbose == True:
            print('Edge coloring is not minimal')
    return g


def draw_edge_coloring(g: nx.Graph, with_labels=False, spectral=False) -> None:
    colors = [g[u][v]['color'] for u, v in g.edges]
    if max(colors) <= 4:  # Specific to kagome
        # Use custom edge colors
        blue, orange, red, green, purple, grey = '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#d3d3d3'
        color_map = {0: blue, 4: purple, 3: orange, 2: green, 1: red}
        for ind, color in enumerate(colors):
            colors[ind] = color_map[color]

    if spectral == False:
        nx.draw_kamada_kawai(g, edge_color=colors, width=5,
                             node_size=20, with_labels=with_labels)
    elif spectral == True:
        nx.draw_spectral(g, edge_color=colors, width=5,
                         node_size=20, with_labels=with_labels)


def heis_circuit(g: nx.Graph, p: int) -> QuantumCircuit:
    """
    Return parameterized ansatz qiskit circuit for the HAFM on the networkx.Graph g, with p cycles. The edges
    of g must have a 'color' attribute that specifies the color by an int, the lowest color being 0. Singlets
    are created along those edges with color 0. Subsequently, HEIS gates are added for the colors c-1,..., 0 in
    sequence, with c the number of different edge colors. This (excluding singlet preparation) is repeated p times.
    This means that for $p = 0$, only the initial state is prepared.
    """
    n = len(g.nodes())
    # Sort edges by color.
    sorted_edges = sorted(g.edges(data=True), key=lambda e: e[2]['color'])
    sorted_edges = list(reversed(sorted_edges))  # Put 'high' colors first.
    qc = QuantumCircuit(n)

    # Prepare the initial state.
    for edge in sorted_edges:
        if edge[2]['color'] == 0:
            qc.append(prepare_singlet(), edge[:2])

    # Add p cycles of parameterized gates.
    par_count = 0
    for _ in range(p):
        for edge in sorted_edges:
            par = Parameter('al_{}'.format(par_count))
            qc.append(heis_gate(par), edge[:2])
            par_count += 1

    # Our routing technique, explained later, assumes circuits with a connected coupling graph. If p = 0, pad the circuit with identity gates to make the coupling graph connected.
    if p == 0:
        for edge in sorted_edges:
            qc.append(pad_gate(), edge[:2])

    return qc


def benchmark(name='kagome', size=(1, 1), circuit_type='quantum_simulation', p=1, repetitions=16, optimization_level=1, methods=['sabre']):
    """
    Run benchmark. Parameters as described in the notebook line_graph_routing.ipynb.
    There is a bug in Qiskit causing the method `lookahead` to run for more than an hour even for the 1x1 kagome patch with a quantum simulation circuit of p=1.
    """
    def get_num_swaps(qc):
        return qc.count_ops()['swap']

    if name == 'kagome':
        lg = kagome(*size)
    elif name == 'shuriken':
        lg = shuriken(*size)
    elif name == 'checkerboard':
        lg = checkerboard(*size)
    elif name == 'complete':
        lg = nx.complete_graph(size)

    if circuit_type == 'quantum_simulation':
        lg = edge_coloring(lg, verbose=False)
        qc = heis_circuit(lg, p)
        basis_gates = ['swap', 'singlet', 'heis']
    elif circuit_type == 'random':
        qc = random_circuit(lg, p)
        basis_gates = ['swap', 'cx', 'h', 's', 't']

    #print('input circuit:')
    # print(qc.draw(fold=-1))
    table = []

    # Line-graph route the quantum simulation circuit.
    method = 'line-graph'
    start = time()
    qc_lgr = line_graph_route(qc)
    end = time()
    #print('line-graph routed:')
    # print(qc_lgr.draw(fold=-1))

    table.append({
        'method': method,
        'num_swaps': get_num_swaps(qc_lgr),
        'num_swaps_CI': 0,
        'min_swaps': get_num_swaps(qc_lgr),
        'depth': qc_lgr.depth(),
        'depth_CI': 0,
        'min_depth': qc_lgr.depth(),
        'num_qubits': qc_lgr.num_qubits,
        'num_qubits_CI': 0,
        'min_qubits': qc_lgr.num_qubits,
        'total_wall_clock': np.round(end-start, 2),
        'wall_clock': np.round(end-start, 2),
        'wall_clock_CI': 0,
        'min_wall_clock': np.round(end-start, 2)
    })

    # Specify hardware coupling map for the other routing methods.
    # Convenient way of getting the target coupling graph.
    cg_lgr = coupling_graph(qc_lgr)
    cg_lgr = nx.convert_node_labels_to_integers(cg_lgr)
    couplinglist = list(cg_lgr.edges)
    couplinglist = couplinglist+[edge[::-1] for edge in cg_lgr.edges]
    coupling_map = CouplingMap(couplinglist=couplinglist)

    # preset_passmanagers.plugin.list_stage_plugins('routing')
    for method in methods:
        #print('Running',method,'routing method')
        wall_clocks = []
        num_qubits = []
        num_swaps = []
        depths = []
        if method == 'basic':
            reps = 1
        else:
            reps = repetitions
        for rep in range(reps):
            start = time()
            qc_alt = transpile(qc, routing_method=method, coupling_map=coupling_map,
                               basis_gates=basis_gates, optimization_level=optimization_level)
            end = time()
            qc_alt = remove_idle_qwires(qc_alt)
            qc_alt = DoubleSwapRemover()(qc_alt)
            qc_alt = OuterSwapRemover()(qc_alt)
            wall_clocks.append(np.round(end-start, 2))
            num_qubits.append(qc_alt.num_qubits)
            num_swaps.append(get_num_swaps(qc_alt))
            depths.append(qc_alt.depth())

        #print('alt routed:')
        # print(qc_alt.draw(fold=-1))

        if method == 'basic':
            wall_clock_CI = 0
            num_qubits_CI = 0
            num_swaps_CI = 0
            depth_CI = 0
        else:
            wall_clock_bs = bootstrap([wall_clocks], np.mean)
            wall_clock_low = wall_clock_bs.confidence_interval.low
            wall_clock_high = wall_clock_bs.confidence_interval.high
            wall_clock_CI = wall_clock_high-wall_clock_low

            num_qubits_bs = bootstrap([num_qubits], np.mean)
            num_qubits_low = num_qubits_bs.confidence_interval.low
            num_qubits_high = num_qubits_bs.confidence_interval.high
            num_qubits_CI = num_qubits_high-num_qubits_low

            num_swaps_bs = bootstrap([num_swaps], np.mean)
            num_swaps_low = num_swaps_bs.confidence_interval.low
            num_swaps_high = num_swaps_bs.confidence_interval.high
            num_swaps_CI = num_swaps_high-num_swaps_low

            depth_bs = bootstrap([depths], np.mean)
            depth_low = depth_bs.confidence_interval.low
            depth_high = depth_bs.confidence_interval.high
            depth_CI = depth_high-depth_low

        min_run = depths.index(min(depths))
        table.append({
            'method': method,
            'num_swaps': get_num_swaps(qc_alt),
            'num_swaps_CI': num_swaps_CI,
            'min_swaps': num_swaps[min_run],
            'depth': np.mean(depths),
            'depth_CI': depth_CI,
            'min_depth': depths[min_run],
            'num_qubits': np.mean(num_qubits),
            'num_qubits_CI': num_qubits_CI,
            'min_qubits': num_qubits[min_run],
            'total_wall_clock': sum(wall_clocks),
            'wall_clock': np.mean(wall_clocks),
            'wall_clock_CI': wall_clock_CI,
            'min_wall_clock': wall_clocks[min_run]
        })

    return [name, size, circuit_type, p, repetitions, optimization_level], table


def print_benchmark(result):
    option, table = result
    #table.sort(key=lambda x: x['num_swaps'])
    formatted_table = []

    def pm_format(lst, key, pm_key):
        s = '{} \u00b1 {}'.format(
            np.round(lst[key], 2), np.round(lst[pm_key]/2, 2))
        return s

    for line in table:
        newline = [
            line['method'],
            pm_format(line, 'num_swaps', 'num_swaps_CI'),
            line['min_swaps'],
            pm_format(line, 'depth', 'depth_CI'),
            line['min_depth'],
            pm_format(line, 'num_qubits', 'num_qubits_CI'),
            line['min_qubits'],
            line['total_wall_clock'],
            pm_format(line, 'wall_clock', 'wall_clock_CI'),
            line['min_wall_clock']
        ]
        formatted_table.append(newline)

    headers = ['method', 'av. n_swaps', 'min. n_swap', 'av. depth', 'min. depth',
               'av. n_qubits', 'min. qubits', 'total time (s)', 'av. time (s)', 'min. time (s)']
    print_table = tabulate(formatted_table, headers=headers)

    print('{\\tiny')
    print('-'*150)
    print('name = {}, size = {}, circuit_type = {}, p = {}, repetitions = {}, optimization_level = {}'.format(*option))
    print()
    print(print_table, flush=True)
    print('-'*150)
    print('}')
    print()
