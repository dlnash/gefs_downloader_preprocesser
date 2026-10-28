"""
Filename:    getGEFS_batch.py
Author:      Deanna Nash, dnash@ucsd.edu
Description: Download GEFS data based on input configuration dictionary.

"""
import sys
import yaml
import subprocess

sys.path.append('../../modules')
import globalvars

### Imports config name from argument when submit
yaml_doc = sys.argv[1]
config_name = sys.argv[2]

# import configuration file for dictionary choice
config = yaml.load(open(yaml_doc), Loader=yaml.SafeLoader)
ddict = config[config_name]

init_date = ddict['init_date']
data_name = ddict['data_name']
ens = ddict['ens']

## run download_GEFS.sh to download data 
bash_script = f"{globalvars.path_to_repo}downloads/GEFS/download_GEFS.sh"
print(subprocess.run([bash_script, init_date, data_name, ens]))