#!/bin/bash
#SBATCH --account=cwp140
#SBATCH --partition=shared-128
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=1
#SBATCH --job-name=download_gefs
#SBATCH -o slurm_out/download_%a.out
#SBATCH -e slurm_out/download_%a.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=dnash@ucsd.edu
#SBATCH --array=0-31   # (32 total members)

PYTHON="/home/dnash/miniconda3/envs/SEAK-impacts/bin/python"
DATE=$1

if [ ${SLURM_ARRAY_TASK_ID} -eq 0 ]; then
    MEMBER="geavg"

elif [ ${SLURM_ARRAY_TASK_ID} -eq 1 ]; then
    MEMBER="gec00"

else
    MEM_NUM=$(printf "%02d" $((${SLURM_ARRAY_TASK_ID} - 1)))
    MEMBER="gep${MEM_NUM}"
fi

echo "Downloading ${MEMBER} for ${DATE}"

$PYTHON ../scripts/download_gefs.py $DATE $MEMBER