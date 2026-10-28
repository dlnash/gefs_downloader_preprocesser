"""
Filename:    GEFS_funcs.py
Author:      Deanna Nash, dnash@ucsd.edu
Description: Functions for preprocessing GEFS data
"""

import os, sys
import xarray as xr
import numpy as np
import pandas as pd


def calc_prec_rate(ds):
    ## convert precipitation to mm per hour
    ts_3hr = pd.timedelta_range(start='0 day', periods=57, freq='3h')
    ts_6hr = pd.timedelta_range(start='0 day', periods=29, freq='6h')
    tp = ds.tp ## pull out tp
    prec_3hr = tp.sel(step=ts_3hr[1::2]) ## grab only the 3hr values
    tp2 = tp.diff(dim='step') ## calculate difference in precip
    ## the values for 6hr timesteps are correct, the values for 3hr timesteps are incorrect
    prec_6hr = tp2.sel(step=ts_6hr[1:]) # grab only the 6hr values
    new_prec = prec_3hr.combine_first(prec_6hr) # combine the correct 3hr values with the correct 6hr values
    ds = ds.drop_vars(["tp"]) # get rid of old tp (accumulated variable)
    ds = xr.merge([ds, new_prec]) # merge dataset with new tp

    return ds

    
def read_GEFS_pres_grb(F, vardict, path_to_data):
    
    ## open pgrb2a data
    fname = path_to_data / f"geavg.t00z.pgrb2a.0p50.f{F}"
    dsa = xr.open_dataset(fname, engine='cfgrib',filter_by_keys=vardict, decode_timedelta=True)
    
    ## open pgrb2b data
    ens_lst = ['gec00']
    for e, ens_mem in enumerate(np.arange(1, 31, 1)):
        ens = 'gep{0}'.format(str(ens_mem).zfill(2))
        ens_lst.append(ens)
    
    ds_lst = []
    for e, ens in enumerate(ens_lst):
        fname = path_to_data / f"{ens}.t00z.pgrb2b.0p50.f{F}"
        ds = xr.open_dataset(fname, engine='cfgrib',filter_by_keys=vardict, decode_timedelta=True)
        ds_lst.append(ds)
    
    ## concat pgrb2b data along pressure level
    dsb = xr.concat(ds_lst, dim='number')
    
    ## calculate ensemble average
    dsb = dsb.mean('number')
    
    ## concat pgrb2a and pgrb2b
    ds = xr.concat([dsa, dsb], dim='isobaricInhPa')
    ds = ds.sortby('isobaricInhPa', ascending=False)
    
    ## subset to 1000 to 200 hPa (for IVT calculation)
    ds = ds.sel(isobaricInhPa=slice(1000, 200))
    return ds

def specific_humidity(temperature, pressure, relative_humidity):
    """
    Author: Brian Kawzenuk

    Calculate specific humidity.
    
    Parameters:
    - temperature: temperature in Kelvin
    - pressure: pressure in Pa
    - relative_humidity: relative humidity as a fraction (e.g., 0.5 for 50%)
    
    Returns:
    - specific humidity
    """

    # Constants
    epsilon = 0.622  # Ratio of molecular weight of water vapor to dry air

    # Calculate saturation vapor pressure
    e_s = 611.2 * np.exp(17.67 * (temperature - 273.15) / (temperature - 29.65))

    # Calculate vapor pressure
    e = relative_humidity * e_s
    # Calculate specific humidity
    q = epsilon * e / (pressure - e)
    
    return q

def calc_IVT_manual(ds):
    '''
    Calculate IVT manually (not using scipy.integrate)
    This is in case you need to remove values below the surface
     '''
    
    pressure = ds.isobaricInhPa.values*100 # convert from hPa to Pa
    dp = np.diff(pressure) # delta pressure
    g = 9.81 # gravity constant
    
    qu_lst = []
    qv_lst = []
    # enumerate through pressure levels so we select the layers
    for i, pres in enumerate(ds.isobaricInhPa.values[:-1]):
        pres2 = ds.isobaricInhPa.values[i+1]
        tmp = ds.sel(isobaricInhPa=[pres, pres2]) # select layer
        tmp = tmp.mean(dim='isobaricInhPa', skipna=True) # average q, u, v in layer
        # calculate ivtu in layer
        qu = ((tmp.q*tmp.u*dp[i])/g)*-1
        qu_lst.append(qu)
        # calculate ivtv in layer
        qv = ((tmp.q*tmp.v*dp[i])/g)*-1
        qv_lst.append(qv)
    
    ## add up u component of ivt from each layer
    qu = xr.concat(qu_lst, pd.Index(pressure[:-1], name="pres"))
    qu = qu.sum('pres')
    qu.name = 'ivtu'
    
    # ## add up v component of ivt from each layer
    qv = xr.concat(qv_lst, pd.Index(pressure[:-1], name="pres"))
    qv = qv.sum('pres')
    qv.name = 'ivtv'
    
    ## calculate IVT magnitude
    ivt = np.sqrt(qu**2 + qv**2)
    ivt.name = 'ivt'

    ds = xr.merge([qu, qv, ivt], compat='no_conflicts')
    
    return ds

def read_GEFS_pgrb2b(F, vardict, path_to_data):
    ## open pgrb2b data
    ens_lst = ['gec00']
    for e, ens_mem in enumerate(np.arange(1, 31, 1)):
        ens = 'gep{0}'.format(str(ens_mem).zfill(2))
        ens_lst.append(ens)
    
    ds_lst = []
    for e, ens in enumerate(ens_lst):
        fname = path_to_data / f"{ens}.t00z.pgrb2b.0p50.f{F}"
        ds = xr.open_dataset(fname, engine='cfgrib',filter_by_keys=vardict, decode_timedelta=True)
        ds_lst.append(ds)
    
    ## concat pgrb2b data along pressure level
    dsb = xr.concat(ds_lst, dim='number')
    
    ## calculate ensemble average
    dsb = dsb.mean('number')

    return dsb