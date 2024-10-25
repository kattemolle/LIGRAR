#!/bin/bash
#$ -N bm
#$ -j yes
#$ -pe openmp 5
#$ -l h_vmem=2G

conda activate ligrar
python3 benchmark_checkerboard.py
