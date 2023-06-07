#!/bin/bash
#$ -N bm
#$ -j yes
#$ -pe openmp 5
#$ -l h_vmem=2G

conda activate qiskit
python3 run_benchmark_checkerboard.py



