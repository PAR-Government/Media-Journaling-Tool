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
    response = requests.get(sign_url + "?file=%s&prefix=%s" % (file_name.lower(), prefix), headers=headers)
    if response.status_code == requests.codes.ok:
        url = response.json()["url"]
        downloadFilename = os.path.join(directory, file_name)
        if os.path.exists(downloadFilename):
            os.remove(downloadFilename)
        try:
            urlretrieve(url, downloadFilename)
        except:
            url = url.replace("https://ceph.mediforprogram.com", "http://ceph-s3.medifor.tld:7480")
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

def __add_query_filter(data,name, value,match_operation):
    quotes = '"' if type(value) == str or type(value) == unicode else ''
    comma = ',' if len(data) > 1 else ''
    value = ('true' if value else 'false') if type(value) == bool else value
    return data + '{}"{}": {{"type": "{}", "value": {}{}{} }}'.format(comma, name, match_operation, quotes, value, quotes)

def findAndDownloadImage(apitoken, baseurl, params, directory, exclusions=None,prefix='images', skip=set()):
    try:
        url = baseurl[:-1] if baseurl.endswith('/') else baseurl
        headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
        url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
        data = '{'
        for k,v in params.iteritems():
           data= __add_query_filter(data,k,v,'exact')
        if exclusions is not None:
            for k, v in exclusions.iteritems():
                data = __add_query_filter(data, k, v, 'ne')
        data += '}'
        logging.getLogger('maskgen').info('checking external service APIs for ' + str(params))
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == requests.codes.ok:
            r = json.loads(response.content)
            if 'results' in r:
                for item in r['results']:
                    if os.path.exists(os.path.join(directory,item['file_name'])) or item['file_name'] in skip:
                        continue
                    return get_image(apitoken, item['file_name'], directory, baseurl,prefix=prefix)
    except:
        pass


class BrowserAPI:
    loader = MaskGenLoader()

    def __init__(self):
        pass

    def pull(self, params,directory='.', exclusions=None,prefix='images',skip=set()):
        token = self.loader.get_key('apitoken')
        url = self.loader.get_key('apiurl')
        return findAndDownloadImage(token, url, params,directory, exclusions=exclusions,prefix=prefix,skip=skip)

    def get_url(self, filename):
        """
        Find Remote URL for given filename
        :param filename:
        :return:
        """
        def remove_api(url):
            return url[:(-5 if url.endswith("/api/") else -4)]

        token = self.loader.get_key('apitoken')
        url = self.loader.get_key('apiurl')

        headers = {'Authorization': 'Token ' + token, 'Content-Type': 'application/json'}
        call_url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
        data = {"file_name": {"type": "exact", "value": filename}}
        response = requests.post(call_url, json=data, headers=headers)
        try:
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                img_id = str(r['results'][0]['id'])
            else:
                return ""
        except Exception:
            return ""

        return "/".join([remove_api(url), 'image', img_id])



