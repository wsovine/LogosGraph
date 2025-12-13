"""Download Bible data files from remote sources."""

import logging
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from tqdm import tqdm

from src.config import settings

logger = logging.getLogger(__name__)


def download_file(url: str, dest_path: Path, chunk_size: int = 8192) -> Path:
    """Download a file from URL with progress bar.

    Args:
        url: Source URL to download from.
        dest_path: Local path to save the file.
        chunk_size: Size of chunks for streaming download.

    Returns:
        Path to the downloaded file.

    Raises:
        requests.HTTPError: If the download fails.
    """
    if dest_path.exists():
        logger.info(f"File already exists, skipping: {dest_path}")
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    filename = dest_path.name

    with open(dest_path, "wb") as f:
        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=filename,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                pbar.update(len(chunk))

    logger.info(f"Downloaded: {dest_path}")
    return dest_path


def download_haydock(data_dir: Path | None = None) -> Path:
    """Download and extract Haydock commentary USFM files from GitHub.

    Downloads the ZIP archive from GitHub and extracts to data/raw/haydock/.
    Skips download if the directory already exists with .sfm files.

    Args:
        data_dir: Base directory for data files. Defaults to settings.DATA_DIR.

    Returns:
        Path to the directory containing the extracted USFM files.

    Raises:
        requests.HTTPError: If the download fails.
    """
    if data_dir is None:
        haydock_dir = settings.HAYDOCK_DIR
    else:
        haydock_dir = data_dir / "haydock"

    # Check if already downloaded (look for .sfm files)
    if haydock_dir.exists():
        sfm_files = list(haydock_dir.glob("*.sfm"))
        if sfm_files:
            logger.info(f"Haydock files already exist ({len(sfm_files)} files), skipping download")
            return haydock_dir

    haydock_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading Haydock commentary from {settings.HAYDOCK_ZIP_URL}")
    response = requests.get(settings.HAYDOCK_ZIP_URL, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))

    # Download with progress bar
    buffer = BytesIO()
    with tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        desc="Haydock.zip",
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            buffer.write(chunk)
            pbar.update(len(chunk))

    # Extract ZIP contents
    logger.info("Extracting Haydock files...")
    buffer.seek(0)
    with zipfile.ZipFile(buffer, "r") as zf:
        # ZIP contains a root folder like "ENG-B-Haydock1883-pd-PSFM-main/"
        # Extract only .sfm files to our target directory
        sfm_count = 0
        for member in zf.namelist():
            if member.endswith(".sfm"):
                # Get just the filename, not the full path
                filename = Path(member).name
                target_path = haydock_dir / filename
                with zf.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())
                sfm_count += 1

    logger.info(f"Extracted {sfm_count} USFM files to {haydock_dir}")
    return haydock_dir


def download_all(data_dir: Path | None = None) -> dict[str, Path]:
    """Download all required data files.

    Args:
        data_dir: Directory to save files. Defaults to settings.DATA_DIR.

    Returns:
        Dictionary mapping file names to their paths.
    """
    if data_dir is None:
        data_dir = settings.DATA_DIR

    files = {}

    # Download CPDV Bible JSON
    cpdv_path = data_dir / "CPDV.json"
    files["cpdv"] = download_file(settings.CPDV_URL, cpdv_path)

    # Download TSK cross-references
    tsk_path = data_dir / "cross_references.txt"
    files["tsk"] = download_file(settings.TSK_URL, tsk_path)

    # Download Haydock commentary USFM files
    files["haydock"] = download_haydock(data_dir)

    return files


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_all()