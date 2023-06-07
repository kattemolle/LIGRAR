#!/bin/bash
#$ -N bm_complete
#$ -j yes
#$ -pe openmp 5
#$ -l h_vmem=2G

conda activate qiskit
python3 run_benchmark_complete.py



