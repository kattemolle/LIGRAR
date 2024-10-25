#!/bin/bash
#$ -N checkerboard1.5x1.5_p=2_t=100
#$ -j yes
#$ -pe openmp 1
#$ -l h_vmem=20G
#$ -l h_rt=100:00:00

conda activate ligrar
python3 vs_OLSQ2.py
