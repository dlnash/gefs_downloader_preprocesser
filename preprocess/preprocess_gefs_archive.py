######################################################################
# Filename:    preprocess_gefs_archive.py
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
path_to_data = Path("/cw3e/mead/projects/cwp140/data/")
BASE_OUT = Path(path_to_data, "preprocessed/GEFS_archive")
BASE_IN = Path(path_to_data, f"downloads/GEFS/{init_date}")


def output_path(init_date, variable):
    out_dir = BASE_OUT / variable
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{init_date}_{variable}.nc"


def save_dataset(ds, init_date, variable):
    fname = output_path(init_date, variable)
    print(f"Writing {fname}")
    ds.to_netcdf(fname, format="NETCDF4")

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

def read_multivar_gefs_archive(varname_lst, F):
    ds_lst = []
    for varname in varname_lst:
        ds = gefs.read_GEFS_pres_grb(F, gfs_vardict[varname], BASE_IN)
        ds_lst.append(ds)
    
    ## merge variable datasets into single dataset
    ds = xr.merge(ds_lst, compat='no_conflicts')

    return ds

def standardize_coords(ds):

    rename_dict = {
    k: v
    for k, v in {
        "latitude": "lat",
        "longitude": "lon",
        "tp": "qpf",
        "gh": "freezing_level",
    }.items()
    if k in ds.variables or k in ds.coords
}

    ds = ds.rename(rename_dict)

    ds = ds.assign_coords({
        "lon": (((ds.lon + 180) % 360) - 180)
    })

    ds = ds.sel(
        lat=slice(70, 0),
        lon=slice(-179.5, -60.)
    )

    return ds

def compute_ivt_single(F):
    # also check geavg pgrb2a (surface pressure)
    sfc_file = BASE_IN / f"geavg.t00z.pgrb2a.0p50.f{F}"
    if not sfc_file.exists():
        print(f"Missing surface pressure for F{F}: {sfc_file}")
        return
        
    print(f'....Computing IVT...')
    print('Reading pressure level data ....')
    ## open pgrb2a surface pressure data
    sfc = xr.open_dataset(sfc_file, engine='cfgrib',filter_by_keys=gfs_vardict['sfc_pressure'], decode_timedelta=True)
    
    ## open all pressure variables needed for IVT calculation
    varname_lst = ['u_wind', 'v_wind', 'rh', 'temperature']
    ds_lst = [sfc]
    for varname in varname_lst:
        ds = gefs.read_GEFS_pres_grb(F, gfs_vardict[varname], BASE_IN)
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
    
    return ds_IVT

def preprocess_ivt(init_date, F_lst):
    ds_lst = []

    for F in F_lst:
        F = str(F).zfill(3)

        ds_ivt = compute_ivt_single(F)
        if ds_ivt is not None:
            ds_lst.append(ds_ivt)

    ds = xr.concat(ds_lst, dim="step")

    ## standardize coords / names
    ds = standardize_coords(ds)

    save_dataset(ds, init_date, "ivt")

def compute_uv_single(F, level=1000):
    ## open all pressure variables needed for IVT calculation
    varname_lst = ['u_wind', 'v_wind']
    ds_lst = []
    for varname in varname_lst:
        ds = gefs.read_GEFS_pres_grb(F, gfs_vardict[varname], BASE_IN)
        ds_lst.append(ds)
    
    ## merge variable datasets into single dataset
    ds = xr.merge(ds_lst, compat='no_conflicts')
    
    ## select the 1000 hPa level
    ds = ds.sel(isobaricInhPa=level)

    ## compute uv magnitude
    ds["uv"] = np.sqrt(ds.u**2 + ds.v**2)

    return ds

def preprocess_uv(init_date, F_lst):
    ds_lst = [compute_uv_single(str(F).zfill(3)) for F in F_lst]
    ds = xr.concat(ds_lst, dim="step")
    ## standardize coords / names
    ds = standardize_coords(ds)
    save_dataset(ds, init_date, "uv")

def compute_freezing_single(F):
    ## extract freezing level data
    freezing_level_ds = gefs.read_GEFS_pgrb2b(F, gfs_vardict['freezing_level'], BASE_IN)

    return freezing_level_ds

def preprocess_freezing(init_date, F_lst):
    ds_lst = []

    for F in F_lst:
        ds_lst.append(compute_freezing_single(str(F).zfill(3)))

    ds = xr.concat(ds_lst, dim="step")
    ## standardize coords / names
    ds = standardize_coords(ds)
    
    save_dataset(ds, init_date, "freezing_level")

def preprocess_qpf(init_date):
    
    ds_lst = []

    F_qpf = np.arange(3, 169, 3)

    for F in F_qpf:
        F = str(F).zfill(3)
        fname = BASE_IN / f"geavg.t00z.pgrb2a.0p50.f{F}"
        if not fname.exists():
            print(f"Missing {fname}")
            continue
        else:
            ds = xr.open_dataset(
                fname,
                engine="cfgrib",
                filter_by_keys=gfs_vardict["prec"],
                decode_timedelta=True,
            )
    
            ds = ds.expand_dims("step")
            ds_lst.append(ds)

    ds = xr.concat(ds_lst, dim="step")
    expected_steps = pd.timedelta_range(
    start="3h",
    end="168h",
    freq="3h"
)

    ds = ds.reindex(step=expected_steps)

    ds = gefs.calc_prec_rate(ds)
    ds = standardize_coords(ds)

    save_dataset(ds, init_date, "qpf")

def preprocess_archive(init_date):

    F_lst = np.arange(6, 169, 6)

    # preprocess_ivt(init_date, F_lst)
    # preprocess_uv(init_date, F_lst)
    preprocess_freezing(init_date, F_lst)
    # preprocess_qpf(init_date)

### run code ###
print(f"Processing GEFS archive init_date={init_date}")
preprocess_archive(init_date)