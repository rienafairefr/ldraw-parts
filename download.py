import logging
import os
import shutil
import zipfile
from datetime import timedelta
from distutils.dir_util import copy_tree
from urllib.request import urlretrieve
from xml.etree import ElementTree as ET

import requests
import requests_cache
from git import Repo

requests_cache.install_cache('ldraw_parts', expire_after=timedelta(weeks=2))


def ensure_exists(path):
    """ makes the directory if it does not exist"""
    os.makedirs(path, exist_ok=True)
    return path


logger = logging.getLogger(__name__)

LDRAW_URL = "http://www.ldraw.org/library/updates/%s"
LDRAW_PTRELEASES = "https://www.ldraw.org/cgi-bin/ptreleases.cgi?type=ZIP"


def get_ptreleases():
    ptreleases = ET.parse(requests.get(LDRAW_PTRELEASES).raw)
    return [
        {ch.tag: ch.text for ch in el} for el in ptreleases.findall(".//distribution")
    ]


PTRELEASES = get_ptreleases()
BASE = "2002-00"  # version 0.27
VERSIONS = (
        ["0.27"]
        + [el["release_id"] for el in PTRELEASES if el["release_id"] >= BASE]
        + ["latest"]
)


def unpack_version(version, zips_dir, versions_dir):
    version_dir = os.path.join(versions_dir, version)
    if not os.path.exists(version_dir):
        version_zip = os.path.join(zips_dir, f"{version}.zip")
        print(f"unzipping the zip {version} in {version_dir}...")
        zip_ref = zipfile.ZipFile(version_zip, "r")
        zip_ref.extractall(version_dir)
        zip_ref.close()


def download_single_version(version, zips_dir):
    if version == "latest":
        filename = "complete.zip"
    elif version == "0.27":
        filename = "ldraw027.zip"
    else:
        short_version = version[2:4] + version[5:]
        filename = f"lcad{short_version}.zip"

    ldraw_url = LDRAW_URL % filename

    retrieved = os.path.join(zips_dir, f"{version}.zip")
    if not os.path.exists(retrieved):
        print(f'retrieving {version}...')
        retrieved_, _ = urlretrieve(ldraw_url)
        shutil.copy(retrieved_, retrieved)


def previous_merge(version):
    logger.debug("recursive_merge")
    ensure_exists(os.path.join("full_versions", version))
    previous_versions = [up for up in VERSIONS if up <= version]
    for previous_version in previous_versions:
        if os.path.exists(os.path.join("full_versions", version)):
            continue
        print(f'{previous_version} => {version}')
        copy_tree(
            os.path.join("versions", previous_version),
            os.path.join("full_versions", version)
        )


def download_all_zip():
    ensure_exists("zips")
    for update in VERSIONS:
        download_single_version(update, "zips")


def unpack_all_zip():
    ensure_exists("versions")
    for update in VERSIONS:
        unpack_version(update, "zips", "versions")


def merge_all():
    ensure_exists("full_versions")
    for update in VERSIONS:
        previous_merge(update)


def main():
    download_all_zip()
    unpack_all_zip()
    merge_all()

    ensure_exists("repo")
    repo = Repo.clone_from("git@github.com:rienafairefr/ldraw-parts.git", 'repo')
    git = repo.git

    # initialize 'library' to an orphan root
    git.checkout('--orphan', "library")
    git.commit("--allow-empty", "-m", "initial commit")

    for version in VERSIONS:
        print(f'committing {version}')
        copy_tree(
            os.path.join("full_versions", version),
            "repo"
        )

        git.add("-A")
        git.commit("-m", f"{version}")
        git.tag(version)

    git.push("--set-upstream", "origin", "library")
    git.push("--tags")


if __name__ == '__main__':
    main()
