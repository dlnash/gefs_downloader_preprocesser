import subprocess
from pathlib import Path

date = "20201128"
member = "geavg"
lead = "099"

def download_targeted_file(date, member, lead):
    out_dir = Path("/cw3e/mead/projects/cwp140/data/downloads/GEFS") / date
    out_dir.mkdir(parents=True, exist_ok=True)
    
    s3_path = f"s3://noaa-gefs-pds/gefs.{date}/00/atmos/pgrb2bp5/{member}.t00z.pgrb2b.0p50.f{lead}"
    out_path = out_dir / f"{member}.t00z.pgrb2b.0p50.f{lead}"
    
    subprocess.run([
        "/cw3e/mead/projects/cwp140/aws/local/bin/aws", "s3", "cp",
        s3_path,
        str(out_path),
        "--no-sign-request",
        "--region", "us-east-1"
    ])

download_targeted_file(date, member, lead)