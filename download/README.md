## Download GEFS from Jan 1, 2017 to present day:

Here is a helpful document on downloading GEFS data:
[open-data-docs/docs/noaa/noaa-gefs-pds at main · awslabs/open-data-docs](https://github.com/awslabs/open-data-docs/tree/main/docs/noaa/noaa-gefs-pds)

The GEFS Forecast data is stored in an Amazon S3 bucket in us-east-1 AWS region.

- `noaa-gefs-pds`

There are two sets of grb files `pgrb2a` and `pgrb2b` . Since we want variables to calculate IVT, we need u, v, and q on pressure levels between 1000 and 200 hPa inclusive. We also want surface pressure to remove IVT values below the surface and freezing level. 

### pgrb2a

The filename structure for `pgrb2a` is as follows:

`noaa-gefs-pds/gefs.YYYYMMDD/XX/atmos/pgrb2ap5/geavg.tXXz.pgrb2a.0p50.fVVV/`

- Where `YYYY` = year ,`MM` = month, `DD` = day of the initialization date
- Where `XX` will be (00, 06, 12, 18) corresponding to the four forecasts initialized each day
- Where `VVV` is the forecast lead in hours (000,006, .. , 384)

---

Variables available for `pgrb2a`

https://www.nco.ncep.noaa.gov/pmb/products/gens/gec00.t12z.pgrb2af06.shtml

- U, V, and Q on levels 200, 250, 300, 400, 500, 700, 850, 925, 1000

### pgrb2b

The filename structure for `pgrb2b` is as follows:

`noaa-gefs-pds/gefs.YYYYMMDD/XX/atmos/pgrb2bp5/gAAAA.tXXz.pgrb2b.0p50.fVVV/`

- Where `AAAA` is the ensemble number. For `pgrb2b` there is no `geavg`, so we need to get iteratively `gec00` `gep01` `gep02` … `gep30`
- The other vars (e.g. `YYYY`, `MM`, `DD` , `XX`, and `VVV` are the same as above for `pgrb2a`.

---

Variables available for `pgrb2b` :

https://www.nco.ncep.noaa.gov/pmb/products/gens/gec00.t12z.pgrb2bf06.shtml

- U, V, Q on levels 350, 550, 650, 800, 900, 950, 975
- 0C isotherm or freezing level
- surface pressure