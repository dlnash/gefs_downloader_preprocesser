######################################################################
# Filename:    create_job_configs.py
# Author:      Deanna Nash dnash@ucsd.edu
# Description: Script to create .yaml configuration file to run job_array with slurm for preprocessing GEFS Data
#
######################################################################

## import libraries
import pandas as pd
import numpy as np
import yaml
from itertools import chain
from pathlib import Path

## create list of init dates, data_names, and leads to download in parallel

init_date_lst = ['20250915', '20250919', '20251008']

df = pd.read_csv('../../out/GEFS_dates_download.csv')
requested_dates = (
    pd.to_datetime(df.init_date, format="%Y%m%d")
    .dt.normalize()
    .unique()
)

# Get dates you already have on disk
path_to_preprocessed_GEFS = Path(
    '/cw3e/mead/projects/cwp140/data/preprocessed/GEFS/qpf/'
)

existing_dates = {
    pd.to_datetime(f.name[:8], format="%Y%m%d")
    for f in path_to_preprocessed_GEFS.glob("*.qpf")
}

# Find dates you still need to download
dates_to_download = sorted(
    d for d in requested_dates if d not in existing_dates
)

print(f"Requested dates: {len(requested_dates)}")
print(f"Existing dates:  {len(existing_dates)}")
print(f"To download:    {len(dates_to_download)}")

jobcounter = 0
filecounter = 0
## loop through to create dictionary for each job
d_lst = []
dest_lst = []
njob_lst = []
for date in dates_to_download:
        jobcounter += 1
        d = {"job_{0}".format(jobcounter):
             {"init_date": date.strftime("%Y%m%d"),
              }}
        d_lst.append(d)
        
        if (jobcounter == 999):
            filecounter += 1
            ## merge all the dictionaries to one
            dest = dict(chain.from_iterable(map(dict.items, d_lst)))
            njob_lst.append(len(d_lst))
            ## write to .yaml file and close
            file=open("config_{0}.yaml".format(str(filecounter)),"w")
            yaml.dump(dest,file, allow_unicode=True, default_flow_style=None)
            file.close()
            
            ## reset jobcounter and d_lst
            jobcounter = 0
            d_lst = []
        
## now save the final config
filecounter += 1
## merge all the dictionaries to one
dest = dict(chain.from_iterable(map(dict.items, d_lst)))
njob_lst.append(len(d_lst))
## write to .yaml file and close
file=open("config_{0}.yaml".format(str(filecounter)),"w")
yaml.dump(dest,file, allow_unicode=True, default_flow_style=None)
file.close()

## create calls.txt for config_1(-8)

for i, njobs in enumerate(njob_lst):
    call_str_lst = []
    for j, job in enumerate(range(1, njobs+1, 1)):
        call_string = "/home/dnash/miniconda3/envs/SEAK-impacts/bin/python -u preprocess_GEFS.py config_{0}.yaml 'job_{1}'".format(i+1, j+1)
        call_str_lst.append(call_string)
        
    ## now write those lines to a text file
    with open('calls_{0}.txt'.format(i+1), 'w',encoding='utf-8') as f:
        for line in call_str_lst:
            f.write(line)
            f.write('\n')
        f.close()