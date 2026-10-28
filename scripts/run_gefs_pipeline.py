import argparse
import yaml
from pathlib import Path
import subprocess
from datetime import datetime

def load_config():
    with open("../config/settings.yaml") as f:
        return yaml.safe_load(f)

def normalize_dates(dates):
    """Convert dates to YYYYMMDD strings"""
    normalized = []
    for d in dates:
        try:
            d_str = str(d)
            normalized.append(datetime.strptime(d_str, "%Y%m%d").strftime("%Y%m%d"))
        except ValueError:
            normalized.append(d.strftime("%Y%m%d"))
    return normalized

def downloaded(date, config):
    """Check if all files for this date are downloaded"""
    download_dir = Path(config["data_root"]) / config["download_dir"] / date
    # For simplicity, just check if the folder exists and has files
    return download_dir.exists() and any(download_dir.iterdir())

def preprocessed(date, config):
    """Check if the date is already preprocessed"""
    preprocess_dir = Path(config["data_root"]) / config["preprocess_dir"]
    file_exists = preprocess_dir.glob(f"{date}*.nc")
    return any(file_exists)

def submit_download(date):
    """Submit download job and return SLURM job ID"""
    result = subprocess.run(
        ["sbatch", "../slurm/download.slurm", date],
        capture_output=True,
        text=True
    )
    job_id = result.stdout.strip().split()[-1]
    print(f"Submitted download job {job_id} for {date}")
    return job_id

def submit_preprocess(date, dependency_job_id=None):
    """Submit preprocess job, optionally dependent on download job"""
    cmd = ["sbatch"]
    if dependency_job_id:
        cmd.append(f"--dependency=afterok:{dependency_job_id}")
    cmd.append("../slurm/preprocess.slurm")
    cmd.append(date)
    result = subprocess.run(cmd, capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1]
    print(f"Submitted preprocess job {job_id} for {date} (depends on {dependency_job_id})")
    return job_id

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", nargs="+", required=False, help="List of dates to process")
    args = parser.parse_args()

    config = load_config()

    # Load dates
    if args.dates:
        dates = args.dates
    else:
        dates = config.get("requested_dates", [])
    dates = normalize_dates(dates)

    if not dates:
        print("No dates provided. Nothing to do.")
        return

    for date in dates:
        # Skip preprocessing if already done
        if preprocessed(date, config):
            print(f"{date} already preprocessed. Skipping.")
            continue

        # Submit download if needed
        if downloaded(date, config):
            print(f"{date} already downloaded. Skipping download.")
            dl_job_id = None
        else:
            dl_job_id = submit_download(date)

        # Submit preprocess job (with dependency if download job exists)
        submit_preprocess(date, dependency_job_id=dl_job_id)

if __name__ == "__main__":
    main()