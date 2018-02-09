import logging
import requests
import json
import os
from urllib import urlretrieve
from maskgen.maskgen_loader import MaskGenLoader


def download(file_name, apitoken, directory, url, prefix='images'):
    import requests
    sign_url = url + ('' if url.endswith('/') else '/') + 'sign/'
    headers = {"Content-Type": "application/json", "Authorization": "Token %s" % apitoken}
    response = requests.get(sign_url + "?file=%s&prefix=%s" % (file_name, prefix), headers=headers)
    if response.status_code == requests.codes.ok:
        url = response.json()["url"]
        downloadFilename = os.path.join(directory, file_name)
        if os.path.exists(downloadFilename):
            os.remove(downloadFilename)
        urlretrieve(url, downloadFilename)
        return downloadFilename
    return None

def get_image(apitoken, file, directory, url,prefix='images'):
    try:
        logging.getLogger('maskgen').info("Pull " + file)
        return download(file,apitoken,directory,url,prefix=prefix)
    except Exception as e:
        logging.getLogger('maskgen').critical("Cannot reach external service " + url)
        logging.getLogger('maskgen').error(str(e))
    return None

def findAndDownloadImage(apitoken, baseurl, params, directory, prefix='images', skip=set()):
    try:
        url = baseurl[:-1] if baseurl.endswith('/') else baseurl
        headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
        url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
        data = '{'
        for k,v in params.iteritems():
            quotes = '"' if type(v) == str else ''
            comma = ',' if len(data) > 1 else ''
            v = ('true' if v else 'false') if type(v) == bool else v
            data += '{}"{}": {{"type": "exact", "value": {}{}{} }}'.format(comma,k,quotes,v,quotes)
        data += '}'
        logging.getLogger('maskgen').info('checking external service APIs for ' + str(params))
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == requests.codes.ok:
            r = json.loads(response.content)
            if 'results' in r:
                for item in r['results']:
                    if os.path.exists(os.path.join(directory,item['file_name'])) or \
                        item['file_name'] in skip:
                        continue
                    return get_image(apitoken, item['file_name'], directory, baseurl,prefix=prefix)
    except:
        pass



class BrowserAPI:
    loader = MaskGenLoader()

    def __init__(self):
        pass

    def pull(self, params,directory='.', prefix='images'):
        token = self.loader.get_key('apitoken')
        url = self.loader.get_key('apiurl')
        findAndDownloadImage(token, url, params,directory, prefix=prefix)




