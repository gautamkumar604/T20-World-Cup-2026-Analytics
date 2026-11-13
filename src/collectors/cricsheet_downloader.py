"""
Module for downloading and preserving authorized Cricsheet datasets.

Complies with open data licensing and website terms by fetching official bulk archives
and preserving the raw files intact with cryptographic SHA-256 verification.
"""

import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from config.settings import (
    RAW_DATA_DIR,
    CRICSHEET_T20_MALE_URL,
    CRICSHEET_T20_ALL_URL,
    RAW_ARCHIVE_NAME,
)
from src.utils.logger import get_logger
from src.utils.validator import compute_sha256

logger = get_logger("cricsheet_downloader")


class CricsheetDownloader:
    """Handles downloading and cryptographic preservation of Cricsheet archives."""

    def __init__(self, raw_dir: Path = RAW_DATA_DIR):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": "T20-World-Cup-2026-Analytics/1.0 (Data Research Project; contact@analytics.org)"
        }

    def download_archive(
        self,
        primary_url: str = CRICSHEET_T20_MALE_URL,
        fallback_url: str = CRICSHEET_T20_ALL_URL,
        filename: str = RAW_ARCHIVE_NAME,
        force_download: bool = False,
    ) -> Path:
        """
        Downloads the Cricsheet bulk archive into data/raw/ and calculates its SHA-256 checksum.

        Args:
            primary_url: Direct download link for Men's T20 archive.
            fallback_url: Alternate download link if primary is unavailable.
            filename: Name for the local raw file.
            force_download: If True, re-downloads even if the file exists.

        Returns:
            Path to the downloaded raw archive.
        """
        target_path = self.raw_dir / filename
        checksum_file = self.raw_dir / "checksums.sha256"

        if target_path.exists() and not force_download:
            logger.info("Raw archive already exists at: %s", target_path)
            sha256 = compute_sha256(target_path)
            logger.info("Existing archive SHA-256: %s", sha256)
            return target_path

        urls_to_try = [primary_url, fallback_url]
        download_success = False

        for url in urls_to_try:
            logger.info("Attempting download from: %s", url)
            req = urllib.request.Request(url, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=60) as response, open(
                    target_path, "wb"
                ) as out_file:
                    content_length = response.headers.get("Content-Length")
                    total_size = int(content_length) if content_length else None
                    downloaded = 0
                    chunk_size = 1024 * 1024  # 1 MB chunk

                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = (downloaded / total_size) * 100
                            if downloaded % (5 * chunk_size) == 0 or downloaded >= total_size:
                                logger.info(
                                    "Downloaded %.1f / %.1f MB (%.1f%%)",
                                    downloaded / (1024 * 1024),
                                    total_size / (1024 * 1024),
                                    pct,
                                )

                download_success = True
                logger.info("Download completed successfully: %s", target_path)
                break
            except urllib.error.HTTPError as e:
                logger.warning("HTTP Error %s accessing %s: %s", e.code, url, e.reason)
            except urllib.error.URLError as e:
                logger.warning("Network/URL Error accessing %s: %s", url, e.reason)
            except Exception as e:
                logger.error("Unexpected error during download from %s: %s", url, str(e))

        if not download_success:
            if target_path.exists():
                target_path.unlink()
            raise RuntimeError(
                f"Failed to download Cricsheet dataset from all attempted URLs: {urls_to_try}"
            )

        # Compute and record cryptographic hash
        sha256_hash = compute_sha256(target_path)
        logger.info("Computed SHA-256 hash: %s", sha256_hash)

        # Write or append to checksums.sha256
        with open(checksum_file, "w", encoding="utf-8") as f:
            f.write(f"{sha256_hash}  {filename}\n")
        logger.info("Recorded hash in: %s", checksum_file)

        return target_path


if __name__ == "__main__":
    downloader = CricsheetDownloader()
    archive_path = downloader.download_archive()
    print(f"Archive saved and verified at: {archive_path}")

