## Directory Structure
```
gefs_pipeline/
├── config
│   └── settings.yaml
├── scripts
│   ├── run_gefs_pipeline.py      # main driver
│   ├── download_gefs.py
│   ├── preprocess_gefs.py
│   └── slurm_submit.py
├── modules
│   └── GEFS_funcs.py
└── slurm
    ├── download.slurm
    └── preprocess.slurm
```

## To Run
Run the following to check existing files, submit download jobs, and submit preprocess jobs for dates indicated.

```
python run_gefs_pipeline.py \
    --dates 20251224 20251225 20251208
```