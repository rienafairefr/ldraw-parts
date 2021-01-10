import logging
import os
import shutil
import zipfile
from datetime import timedelta
from subprocess import check_output
from urllib.error import HTTPError
from urllib.request import urlretrieve
from xml.etree import ElementTree as ET

import requests
import requests_cache
from git import Repo, GitCommandError

requests_cache.install_cache('ldraw_parts', expire_after=timedelta(weeks=2))


def ensure_exists(path):
    """ makes the directory if it does not exist"""
    os.makedirs(path, exist_ok=True)
    return path


logger = logging.getLogger(__name__)

LDRAW_URL = "http://www.ldraw.org/library/updates/%s"
LDRAW_PTRELEASES = "https://www.ldraw.org/cgi-bin/ptreleases.cgi"

ARCHIVES_DIR = "archives"
VERSIONS_DIR = "versions"
FULL_VERSIONS_DIR = "full_versions"
SCRATCH_FULL_VERSION_DIR = f"fs/full_version"
REPO_DIR = "fs/repo"


def without_keys(d, keys):
    return {x: d[x] for x in d if x not in keys}


def get_ptreleases():
    ptreleases = ET.parse(requests.get(LDRAW_PTRELEASES).raw)
    releases = [
        {ch.tag: ch.text for ch in el} for el in ptreleases.findall(".//distribution")
    ]
    for r in releases:
        if r['release_id'] == "0.27":
            # "base" release
            r['release_id'] = "2002-00"

    unsorted = {
        r['release_id']: without_keys(r, ["release_id"]) for r in releases
    }

    return dict(sorted(unsorted.items()))


VERSIONS = get_ptreleases()
BASE = "2002-00"  # version 0.27


def unpack_version(version, archives_dir, versions_dir):
    version_dir = os.path.join(versions_dir, version)
    if not os.path.exists(version_dir):
        try:
            version_zip = os.path.join(archives_dir, f"{version}.zip")
            print(f"unzipping the zip {version} in {version_dir}...")
            zip_ref = zipfile.ZipFile(version_zip, "r")
            zip_ref.extractall(version_dir)
            zip_ref.close()
        except OSError:
            version_arj = os.path.join(archives_dir, f"{version}.exe")
            print(f"extracting the ARJ {version} in {version_dir}...")
            check_output(["arj", "x", version_arj, f"{version_dir}/", "*", "-y"])


def download_single_version(version, archives_dir):
    if version == "2002-00":
        filename = "ldraw027"
    else:
        short_version = version[2:4] + version[5:]
        filename = f"lcad{short_version}"

    prefixes = (".zip", ".exe")

    if not any(os.path.exists(os.path.join(archives_dir, f"{version}{prefix}")) for prefix in prefixes):
        for prefix in (".zip", ".exe"):
            try:
                ldraw_url = LDRAW_URL % filename + prefix

                retrieved = os.path.join(archives_dir, f"{version}{prefix}")
                print(f'retrieving {version}...')
                retrieved_, _ = urlretrieve(ldraw_url)
                shutil.copy(retrieved_, retrieved)
                break
            except HTTPError as e:
                if e.code == 404:
                    # only a .exe available
                    continue


def previous_merge(version, full_versions_dir, versions_dir):
    logger.debug("recursive_merge")
    full_version_dir = os.path.join(full_versions_dir, version)
    if os.path.exists(full_version_dir):
        return
    ensure_exists(full_version_dir)
    previous_versions = [rid for rid in VERSIONS if rid <= version]
    for previous_version in previous_versions:
        print(f'{previous_version} => {version}')
        version_dir = os.path.join(versions_dir, previous_version)

        if "ldraw" in (f.lower() for f in os.listdir(version_dir)):
            destination_dir = SCRATCH_FULL_VERSION_DIR
        else:
            # some releases
            destination_dir = os.path.join(SCRATCH_FULL_VERSION_DIR, "ldraw")

        shutil.copytree(
            version_dir,
            destination_dir,
            dirs_exist_ok=True

        )
    shutil.copytree(
        SCRATCH_FULL_VERSION_DIR,
        full_version_dir,
        dirs_exist_ok=True
    )
    empty_dir(SCRATCH_FULL_VERSION_DIR)


def download_all_archives():
    ensure_exists(ARCHIVES_DIR)
    for version in VERSIONS:
        download_single_version(version, ARCHIVES_DIR)


def unpack_all_archives():
    ensure_exists(VERSIONS_DIR)
    for version in VERSIONS:
        unpack_version(version, ARCHIVES_DIR, VERSIONS_DIR)


def merge_all():
    ensure_exists(FULL_VERSIONS_DIR)
    for version in VERSIONS:
        previous_merge(version, FULL_VERSIONS_DIR, VERSIONS_DIR)


def empty_dir(dir):
    for root, dirs, files in os.walk(dir):
        for f in files:
            os.remove(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


def main():
    download_all_archives()
    unpack_all_archives()
    merge_all()

    empty_dir(REPO_DIR)
    repo = Repo.clone_from("git@github.com:rienafairefr/ldraw-parts.git", REPO_DIR)
    git = repo.git

    os.environ['GIT_COMMITTER_NAME'] = git.config('--get', 'user.name')
    os.environ['GIT_COMMITTER_EMAIL'] = git.config('--get', 'user.EMAIL')

    # initialize 'library' to an orphan root
    git.checkout('--orphan', "library")
    git.reset('--hard')

    for version in VERSIONS:
        print(f'committing {version}')
        previous_merge(version, FULL_VERSIONS_DIR, VERSIONS_DIR)
        shutil.copytree(
            os.path.join(FULL_VERSIONS_DIR, version),
            REPO_DIR,
            dirs_exist_ok=True
        )
        shutil.rmtree(os.path.join(FULL_VERSIONS_DIR, version))

        git.add("-A")
        git.commit(f"--date={VERSIONS[version]['release_date']}", "--author", "PTAdmin <parts@ldraw.org>", "-m", f"{version}")
        git.tag("-f", version)

    git.push("--set-upstream", "origin", "library")
    git.push("--force", "--tags")


if __name__ == '__main__':
    main()
