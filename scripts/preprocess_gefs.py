######################################################################
# Filename:    preprocess_GEFS.py
# Author:      Deanna Nash dnash@ucsd.edu
# Description: Script to take downloaded GEFS u, v, rh, and t data for each given init date and lead time, 
# preprocess IVT data and save as single netCDF file, extract and save freezing level data
#
######################################################################

## import libraries
import os, sys
import subprocess
import yaml
import xarray as xr
import numpy as np
import pandas as pd
import shutil
from pathlib import Path

sys.path.append('../modules')
import GEFS_funcs as gefs

init_date = sys.argv[1]

with open("../config/settings.yaml") as f:
    config = yaml.safe_load(f)

F_lst = np.arange(
    config["forecast_hour_start"],
    config["forecast_hour_end"] + 1,
    config["forecast_hour_step"]
)

data_root = Path(config["data_root"])
path_to_data = data_root / config["download_dir"] / init_date
path_to_out = data_root / config["preprocess_dir"] / init_date
path_to_out.mkdir(parents=True, exist_ok=True)

for subdir in ["UV1000", "IVT", "freezing_level", "qpf"]:
    (path_to_out / subdir).mkdir(parents=True, exist_ok=True)

## dictionary of variables we need
gfs_vardict = {
"u_wind":{"typeOfLevel":'isobaricInhPa',"shortName":"u"}, #U-component of wind
"v_wind":{"typeOfLevel":'isobaricInhPa',"shortName":"v"}, #V-component of wind
"temperature":{"typeOfLevel":'isobaricInhPa',"shortName":"t"}, #Temperature
"rh":{"typeOfLevel":'isobaricInhPa',"shortName":"r"}, #Relative Humidity
"sfc_pressure":{'name': 'Surface pressure', 'typeOfLevel': 'surface', 'level': 0, 'paramId': 134, 'shortName': 'sp'}, #surface pressure
"freezing_level": {'typeOfLevel': 'isothermZero', 'shortName': 'gh'}, ## freezing level
"prec":{'name': 'Total Precipitation', 'typeOfLevel': 'surface', 'level': 0, 'paramId': 228228, 'shortName': 'tp'} #total precipitation

}

# --- Functions ---
def download_targeted_file(date, member, lead, data_name):

    if data_name == "pgrb2a":
        subdir = "pgrb2ap5"
    elif data_name == "pgrb2b":
        subdir = "pgrb2bp5"
    else:
        raise ValueError(f"Unknown data_name: {data_name}")

    s3_path = f"s3://noaa-gefs-pds/gefs.{date}/00/atmos/{subdir}/{member}.t00z.{data_name}.0p50.f{lead}"
    out_path = path_to_data / f"{member}.t00z.{data_name}.0p50.f{lead}"

    for attempt in range(3):
        result = subprocess.run([
        "/cw3e/mead/projects/cwp140/aws/local/bin/aws", "s3", "cp",
        s3_path,
        str(out_path),
        "--no-sign-request",
        "--region", "us-east-1"
    ])
        if result.returncode == 0:
            break
    
def get_required_members(data_name):

    if data_name == "pgrb2a":
        members = ["geavg", "gec00"]
        members += [f"gep{str(i).zfill(2)}" for i in range(1, 31)]

    elif data_name == "pgrb2b":
        members = ["gec00"]
        members += [f"gep{str(i).zfill(2)}" for i in range(1, 31)]

    else:
        raise ValueError(f"Unknown data_name: {data_name}")

    return members
    
def output_exists(path):
    if path.exists():
        print(f"Skipping existing file: {path.name}")
        return True
    return False

def inputs_complete(F, data_name):
    members = get_required_members(data_name)
    all_present = True

    for m in members:
        fname = path_to_data / f"{m}.t00z.{data_name}.0p50.f{F}"
        if not fname.exists():
            print(f"Missing {m} for F{F}")
            all_present = False
            download_targeted_file(init_date, m, F, data_name)

    return all_present
    
def compute_uv1000(F):
    ######################
    ### COMPUTE UV1000 ###
    ######################
    # check if we already processed this file
    out_fname = path_to_out / f"{init_date}.t00z.0p50.f{F}.UV1000.nc" 
    if output_exists(out_fname): 
        return

    # check if we have all the data we need
    if not inputs_complete(F, "pgrb2a"):
        print(f"Skipping UV1000 F{F} due to missing inputs")
        return
        
    print(f'....Computing UV1000...')
    ## open all pressure variables needed for IVT calculation
    varname_lst = ['u_wind', 'v_wind']
    ds_lst = []
    for varname in varname_lst:
        ds = gefs.read_GEFS_pres_grb(F, gfs_vardict[varname], path_to_data)
        ds_lst.append(ds)
    
    ## merge variable datasets into single dataset
    ds = xr.merge(ds_lst, compat='no_conflicts')
    
    ## select the 1000 hPa level
    ds = ds.sel(isobaricInhPa=1000)
    
    ## save data to netCDF file
    print('Writing {0} to netCDF ....'.format('UV1000'))
    ds.to_netcdf(path=out_fname, mode = 'w', format='NETCDF4')
    ds.close()
    del ds, ds_lst

    
def compute_ivt(F):
    ###################
    ### COMPUTE IVT ###
    ###################
    # check if we already processed this file
    out_fname = path_to_out / f"{init_date}.t00z.0p50.f{F}.IVT.nc" 
    if output_exists(out_fname): 
        return
        
    # check if we have all the data we need
    if not inputs_complete(F, "pgrb2a"):
        print(f"Skipping IVT F{F} due to missing inputs")
        return

    # also check geavg pgrb2a (surface pressure)
    sfc_file = path_to_data / f"geavg.t00z.pgrb2a.0p50.f{F}"
    if not sfc_file.exists():
        print(f"Missing surface pressure for F{F}")
        return
        
    print(f'....Computing IVT...')
    print('Reading pressure level data ....')
    ## open pgrb2a surface pressure data
    sfc = xr.open_dataset(sfc_file, engine='cfgrib',filter_by_keys=gfs_vardict['sfc_pressure'], decode_timedelta=True)
    
    ## open all pressure variables needed for IVT calculation
    varname_lst = ['u_wind', 'v_wind', 'rh', 'temperature']
    ds_lst = [sfc]
    for varname in varname_lst:
        ds = gefs.read_GEFS_pres_grb(F, gfs_vardict[varname], path_to_data)
        ds_lst.append(ds)
    
    ## merge variable datasets into single dataset
    ds = xr.merge(ds_lst, compat='no_conflicts')
    
    ## Compute specific humidity from relative humidity and temperature
    print('Computing specific humidity ....')
    #extending pressure vector to 3d array to match rh shape
    pressure_3d = np.tile(ds["r"].isobaricInhPa.values[:, np.newaxis, np.newaxis], (1, ds["r"].values.shape[1], ds["r"].values.shape[2]))
    
    q = gefs.specific_humidity(temperature=ds["t"].values, pressure=pressure_3d*100, relative_humidity=ds["r"].values/100)
    
    ## put into dataarray and add to dataset
    q = xr.DataArray(q, name="q", dims=( "isobaricInhPa", "latitude","longitude"), 
                     coords={"latitude": ds.latitude.values, "longitude":ds.longitude.values,
                            "isobaricInhPa": ds.isobaricInhPa.values})
    ds['q'] = q
    
    ## drop t and rh since we don't need them anymore
    ds = ds.drop_vars(['t', 'r'])
    
    ## mask values below surface pressure
    print('Masking values below surface ....')
    varlst = ['q', 'u', 'v']
    for varname in varlst:
        mask = ds.isobaricInhPa < (ds.sp / 100.).expand_dims({"isobaricInhPa": ds.isobaricInhPa})
        ds[varname] = ds[varname].where(mask)
    
    ## integrate to calculate IVT
    print('Calculating IVT ....')
    ds_IVT = gefs.calc_IVT_manual(ds) # calculate IVT
    
    ## save data to netCDF file
    print('Writing {0} to netCDF ....'.format('IVT'))
    ds_IVT.to_netcdf(path=out_fname, mode = 'w', format='NETCDF4')

    ds.close()
    ds_IVT.close()
    del ds, ds_lst
    
def compute_freezing_level(F):
    # check if we already processed this file
    out_fname = path_to_out / f"{init_date}.t00z.0p50.f{F}.freezing_level.nc" 
    if output_exists(out_fname): 
        return

    # check if we have all the data we need
    if not inputs_complete(F, "pgrb2b"):
        print(f"Skipping freezing level F{F}")
        return
        
    ##############################
    ### COMPUTE FREEZING LEVEL ###
    ##############################
    print(f'....Computing Freezing Level...')
    ## extract freezing level data
    freezing_level_ds = gefs.read_GEFS_pgrb2b(F, gfs_vardict['freezing_level'], path_to_data)
    
    ## save data to netCDF file
    print('Writing {0} to netCDF ....'.format('Freezing Level'))
    freezing_level_ds.to_netcdf(path=out_fname, mode = 'w', format='NETCDF4')

    freezing_level_ds.close()
    del freezing_level_ds

    
for F in F_lst:
    F = str(F).zfill(3)
    print(f'Processing Lead {F}...')
    compute_uv1000(F)
    compute_ivt(F)
    compute_freezing_level(F)

###################
### COMPUTE QPF ###
###################
print(f'....Computing QPF...')
## Read QPF data for all time steps
ds_lst = []
F_qpf = np.arange(3, config["forecast_hour_end"] + 1, 3)
for F in F_qpf:
    try:
        F = str(F).zfill(3)
        fname = path_to_data / f"geavg.t00z.pgrb2a.0p50.f{F}"
        if not fname.exists():
            print(f"Missing file: {fname}")
            continue
        dsa = xr.open_dataset(fname, engine='cfgrib',filter_by_keys=gfs_vardict['prec'], decode_timedelta=True)
        dsa = dsa.expand_dims(dim='step')
        ds_lst.append(dsa)
    except Exception as e:
        print(f"Warning: issue reading F={F}: {e}")
        # Subtract 3 hours from 'step' and 'valid_time' coordinates
        dsa = dsa.assign_coords(
        step=dsa.step + np.timedelta64(3, 'h'),
        valid_time=dsa.valid_time + np.timedelta64(3, 'h'))
        ds_lst.append(dsa)

if len(ds_lst) == 0:
    print("No QPF files found, skipping QPF computation")
else:
    ds = xr.concat(ds_lst, dim='step')

## fix lons 
ds = ds.assign_coords({"longitude": (((ds.longitude + 180) % 360) - 180)}) # Convert DataArray longitude coordinates from 0-359 to -180-179
## subset to N. America [0, 70, 180, 295]
ds = ds.sel(latitude=slice(70, 0), longitude=slice(-179.5, -60.))
## run preprocess
ds = gefs.calc_prec_rate(ds)

## save as netCDF
## save data to netCDF file
print('Writing {0} to netCDF ....'.format('qpf'))
out_fname = path_to_out / "qpf" / f"{init_date}.t00z.0p50.f003-f168.qpf.nc"
ds.to_netcdf(path=out_fname, mode = 'w', format='NETCDF4')

ds.close()
del ds, ds_lst

