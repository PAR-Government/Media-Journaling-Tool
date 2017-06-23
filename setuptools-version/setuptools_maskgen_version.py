from pkg_resources import get_distribution
from subprocess import check_output
import requests
import json

repos = 'rwgdrummer/maskgen'
giturl = 'https://api.github.com/repos'

def get_commit():
    url = giturl + '/' + repos + '/pulls?state=closed'
    resp = requests.get(url)
    if resp.status_code == requests.codes.ok:
        content = json.loads(resp.content)
        for item in content:
            if 'merged_at' in item and 'merge_commit_sha' in item:
                return  item['merge_commit_sha']
    return None

def get_version():
    import os
    filename = 'VERSION'
    #if os.path.exists('.git/ORIG_HEAD'):
    #    filename = '.git/ORIG_HEAD'
    #else:
    print os.path.abspath(filename)
    with open(filename) as fp:
        return fp.readline()

def validate_version_format(dist, attr, value):
    try:
        version = get_version().strip()
    except:
        version = get_distribution(dist.get_name()).version
    else:
        version = format_version(version=version, fmt=value)
    dist.metadata.version = version


def format_version(version, fmt='{gitsha}'):
    return fmt.format(gitsha=version)

if __name__ == "__main__":
    # determine version from git
    git_version = get_version().strip()
    git_version = format_version(version=git_version)

    # monkey-patch `setuptools.setup` to inject the git version
    import setuptools
    original_setup = setuptools.setup

    def setup(version=None, *args, **kw):
        return original_setup(version=git_version, *args, **kw)

    setuptools.setup = setup

    # import the packages's setup module
    import setup
