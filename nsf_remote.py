"""Compare NSF's published award zips with the local copies without downloading them.

NSF re-stamps every yearly zip each day, so a file's date and size do not say
whether its awards changed. A zip ends with an index of its members and their
checksums; reading only that index (about 0.5 MB per year) over HTTP Range
requests shows exactly which award files are new, changed or gone.

Standard library only, so the login reminder can import it without `uv`.
"""

import dataclasses
import datetime
import io
import json
import urllib.request
import zipfile
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

# NSF's "Download Awards by Year" page gets its signed S3 links from this endpoint.
FILE_LIST_URL = "https://api.nsf.gov/services/v2/s3/list-files"

# Holds the ISO date of the last successful fetch from NSF. It sits beside the
# zips because it describes them: a fresh clone has neither.
LAST_FETCH_PATH = RAW_DIR / "last_fetch.txt"

# Large enough to read a year's index in two or three requests, small enough
# that reading one award does not drag megabytes of its neighbours along.
REMOTE_BUFFER_BYTES = 512 * 1024

NETWORK_TIMEOUT_SECONDS = 60


class RemoteFile(io.RawIOBase):
    """A read-only seekable file served by HTTP Range requests."""

    def __init__(self, url, size):
        super().__init__()
        self.url = url
        self.size = size
        self.position = 0
        self.bytes_fetched = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.position = offset
        elif whence == io.SEEK_CUR:
            self.position += offset
        else:
            self.position = self.size + offset
        return self.position

    def readinto(self, buffer):
        length = min(len(buffer), self.size - self.position)
        if length <= 0:
            return 0
        last_byte = self.position + length - 1
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.position}-{last_byte}"})
        with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            # 200 would mean the server ignored Range and is sending the whole file.
            if response.status != 206:
                raise OSError(f"expected a partial response, got HTTP {response.status}")
            data = response.read()
        buffer[:len(data)] = data
        self.position += len(data)
        self.bytes_fetched += len(data)
        return len(data)


@dataclasses.dataclass
class MemberDiff:
    """Award file names that differ between a remote zip and its local copy."""

    added: list
    changed: list
    removed: list

    @property
    def total(self):
        return len(self.added) + len(self.changed) + len(self.removed)


def fetch_file_listing():
    """Return NSF's current files as {file name: entry}; an entry has downloadUrl and size."""
    with urllib.request.urlopen(FILE_LIST_URL, timeout=NETWORK_TIMEOUT_SECONDS) as response:
        listing = json.load(response)
    return {entry["fileName"]: entry for entry in listing["files"]}


def tracked_year_file_names(listing):
    """Year zips to keep current: the ones already local, plus any newer year NSF has added.

    Older years are left out on purpose; which past years to cover is a choice
    made once with `download`, not something an update should widen.
    """
    local_years = sorted(int(path.stem) for path in RAW_DIR.glob("*.zip") if path.stem.isdigit())
    if not local_years:
        return []
    newest_local_year = local_years[-1]
    remote_years = sorted(int(name[:-4]) for name in listing if name.endswith(".zip") and name[:-4].isdigit())
    newer_remote_years = [year for year in remote_years if year > newest_local_year]
    return [f"{year}.zip" for year in local_years + newer_remote_years]


def open_remote_zip(entry):
    """Open one listed zip for reading over the network; only the index is fetched up front."""
    remote_file = RemoteFile(entry["downloadUrl"], int(entry["size"]))
    return zipfile.ZipFile(io.BufferedReader(remote_file, buffer_size=REMOTE_BUFFER_BYTES))


def diff_against_local(remote_zip, local_zip_path):
    """Compare a remote zip's members with the local zip at `local_zip_path` by checksum.

    A missing local zip counts every remote member as added.
    """
    remote_checksums = {info.filename: info.CRC for info in remote_zip.infolist() if info.filename.endswith(".json")}
    local_checksums = {}
    if local_zip_path.exists():
        with zipfile.ZipFile(local_zip_path) as local_zip:
            local_checksums = {info.filename: info.CRC for info in local_zip.infolist() if info.filename.endswith(".json")}
    added = [name for name in remote_checksums if name not in local_checksums]
    changed = [
        name for name, checksum in remote_checksums.items()
        if name in local_checksums and local_checksums[name] != checksum
    ]
    removed = [name for name in local_checksums if name not in remote_checksums]
    return MemberDiff(added=added, changed=changed, removed=removed)


def read_last_fetch_date():
    """Return the date of the last successful fetch from NSF, or None if there has been none."""
    if not LAST_FETCH_PATH.exists():
        return None
    return datetime.date.fromisoformat(LAST_FETCH_PATH.read_text().strip())


def write_last_fetch_date(fetch_date):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LAST_FETCH_PATH.write_text(fetch_date.isoformat() + "\n")
