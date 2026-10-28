#!/bin/bash
#SBATCH --account=cwp140
#SBATCH --partition=shared-128
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --job-name=preprocess_gefs
#SBATCH -o slurm_out/preprocess_%A.out
#SBATCH -e slurm_out/preprocess_%A.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=dnash@ucsd.edu

DATE=$1
PYTHON="/home/dnash/miniconda3/envs/SEAK-impacts/bin/python"
$PYTHON ../scripts/preprocess_gefs.py $DATE