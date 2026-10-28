# download_gefs.py
import sys
from pathlib import Path
import subprocess
import yaml
import numpy as np

date = sys.argv[1]
member = sys.argv[2]

# Load config
with open("../config/settings.yaml") as f:
    config = yaml.safe_load(f)

lead_hours = np.arange(
    config["forecast_hour_start"],
    config["forecast_hour_end"] + 1,
    config["forecast_hour_step"]
)

data_root = Path(config["data_root"])
download_dir = data_root / config["download_dir"] / date
download_dir.mkdir(parents=True, exist_ok=True)

data_name = "pgrb2a" if member == "geavg" else "pgrb2b"

for lead in lead_hours:
    lead_str = f"{lead:03d}"
    s3_path = (
        f"s3://noaa-gefs-pds/gefs.{date}/00/atmos/"
        f"{data_name}p5/{member}.t00z.{data_name}.0p50.f{lead_str}"
    )
    # out = download_dir / f"{member}.f{lead_str}"
    out = download_dir / f"{member}.t00z.{data_name}.0p50.f{lead_str}"

    if out.exists():
        continue

    subprocess.run([
        "/cw3e/mead/projects/cwp140/aws/local/bin/aws",
        "s3",
        "cp",
        s3_path,
        str(out),
        "--no-sign-request",
        "--region",
        "us-east-1"
    ])