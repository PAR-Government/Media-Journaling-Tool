# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import requests
import json
import logging
import maskgen
from maskgen import maskGenPreferences

"""
Git API used to compare version of the tool with lastest on GitHub master
"""

class GitLabAPI:

    def __init__(self,branch='master',version_file='VERSION',repo='',
                 url='https://gitlab.mediforprogram.com'):
        self.file = '{url}/api/v4/projects/{repo}/repository/files/{version_file}/raw'.format(
            url=url, repo=repo, version_file=version_file
        )
        self.commits = '{url}/api/v4/projects/{repo}/repository/commits'.format(
            url=url, repo=repo, version_file=version_file
        )
        self.token = maskGenPreferences.get_key('git.token')
        self.branch = branch


    def get_version_file(self):
        header = {'PRIVATE-TOKEN':self.token}
        resp = requests.get(self.file, params={"ref":self.branch}, timeout=2, headers=header)
        if resp.status_code == requests.codes.ok:
            return resp.content.strip()
        return "NA"

    def getCommitMessage(self):
        import json
        header = {'PRIVATE-TOKEN': self.token}
        resp = requests.get(self.commits, params={"ref": self.branch}, timeout=2, headers=header)
        if resp.status_code == requests.codes.ok:
            data = json.loads(resp.content)
            return data[0]['message']
        return "NA"

class GitHub:

    #TODO!
    def __init__(self,branch='master',version_file='VERSION',repo='',
                 url='https://api.github.com/'):
        self.file = '{url}/repos/{repo}/repository/files/{version_file}/raw'.format(
            url=url, repo=repo, version_file=version_file
        )
        self.commits = '{url}/repos/{repo}/repository/files/{version_file}/raw'.format(
            url=url, repo=repo, version_file=version_file
        )
        self.token = maskGenPreferences.get_key('git.token')
        self.branch = branch

    def get_version_file(self):
        header = {'PRIVATE-TOKEN':self.token}
        resp = requests.get(self.file, params={"ref":self.branch}, timeout=2, headers=header)
        if resp.status_code == requests.codes.ok:
            return resp.content.strip()
        return "NA"

    def getCommitMessage(self):
        url = self.url + '/' + self.repos + '/commits/'
        resp = requests.get(url, timeout=2)
        if resp.status_code == requests.codes.ok:
            content = json.loads(resp.content)
            return content['commit']['message']
        return None


class UpdaterGitAPI:

    def __init__(self, branch='master',version_file='VERSION'):
        url = maskGenPreferences.get_key('git.api.url',
                                              'https://gitlab.mediforprogram.com/')
        repo = maskGenPreferences.get_key('repo','503')
        if 'gitlab' in url:
            self.api = GitLabAPI(branch=branch,version_file=version_file,url=url,repo=repo)
        else:
            self.api = GitHub(branch=branch, version_file=version_file, url=url, repo=repo)

    def _get_version_file(self):
        return self.api.get_version_file()

    def _getCommitMessage(self):
        return self.api.getCommitMessage()

    def _hasNotPassed(self,  merge_sha):
        if merge_sha is None:
            return True
        currentversion = maskgen.__version__
        sha = currentversion[currentversion.rfind('.')+1:]
        return not merge_sha.startswith(sha)

    def isOutdated(self):
        try:
            merge_sha = self._get_version_file()
            if self._hasNotPassed(merge_sha):
                return merge_sha, self._getCommitMessage()
            return None, None
        except Exception as ex:
            logging.getLogger('maskgen').error('Error validating JT version: {}'.format(ex.message))
            raise EnvironmentError(ex.message)

class OperationsUpdaterGitAPI(UpdaterGitAPI):

    def __init__(self, branch='master'):
        import urllib
        UpdaterGitAPI.__init__(self, branch=branch,version_file=urllib.quote_plus('resources/operations.json'))

    def _get_version_file(self):
        resp = UpdaterGitAPI._get_version_file(self)
        if resp is not None:
            import json
            return json.loads(resp)['version']

    def _hasNotPassed(self, merge_sha):
        from maskgen.software_loader import getMetDataLoader
        if merge_sha is None:
            return True
        currentversion = getMetDataLoader().operation_version
        return merge_sha != currentversion



a  = OperationsUpdaterGitAPI()
a._get_version_file()