# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import logging
from core import ValidationAPI,ValidationMessage,Severity

class ValidationBrowserAPI(ValidationAPI):

    def __init__(self,preferences):
        ValidationAPI.__init__(self,preferences)

    def isExternal(self):
        return True

    def isConfigured(self):
        """
        :return: return true if validator is configured an usable
        @rtype: bool
        """
        return 'apiurl' in self.preferences and self.preferences['apiurl'] is not None

    def check_node(self, node, graph):
        """
        CHECK
        (1) The final node unique across all journals.
        (2) Base Node is HP
        :param node: node id
        :param graph: image graph
        :return: list of validation messages
        @type node: str
        @type graph: ImageGraph
        """
        errors=[]
        nodeData = graph.get_node(node)
        isHP = ('cgi' not in nodeData or nodeData['cgi'] == 'no') and ('HP' not in nodeData or nodeData['HP'] == 'yes')
        checked_nodes = graph.getDataItem('api_validated_node', [])
        try:
            if nodeData['file'] not in checked_nodes:
                if nodeData['nodetype'] == 'base' and isHP and \
                                self.preferences.get_key('apitoken') is not None:
                    fields = self.get_media_file(nodeData['file'])
                    if len(fields) == 0:
                        errors.append(ValidationMessage(Severity.ERROR,
                                                        node,
                                                        node,
                                                        "Cannot find base media file {} in the remote system. ".format(nodeData['file']),
                                                        'Browser API',
                                                        None))
                    elif not fields[0]['high_provenance']:
                        errors.append(ValidationMessage(Severity.ERROR,
                                                        node,
                                                        node,
                                                        "{} media is not HP".format(nodeData['file']),
                                                        'Browser API',
                                                        None))
                    else:
                        checked_nodes.append(nodeData['file'])
                        graph.setDataItem('api_validated_node', checked_nodes, excludeUpdate=True)

                if nodeData['nodetype'] == 'final' and \
                                self.preferences.get_key('apitoken') is not None:
                    fields = self.get_media_file(nodeData['file'])
                    if len(fields) > 0:
                        for journal in fields:
                            if journal['manipulation_journal'] is not None and journal['manipulation_journal'] != graph.get_name():
                                errors.append(ValidationMessage(Severity.ERROR,
                                                        node,
                                                        node,
                                                        "Final media node {} used in journal {}".format(nodeData['file'],
                                                                                              journal['manipulation_journal']),
                                                        'Browser API',
                                                        None))
                    else:
                        checked_nodes.append(nodeData['file'])
                        graph.setDataItem('api_validated_node', checked_nodes, excludeUpdate=True)
        except Exception as ex:
            errors.append(ValidationMessage(Severity.ERROR,
                                            node,
                                            node,
                                            "Cannot reach browser API at this time to validate node. See log for details.",
                                            'Browser API',
                                            None))
        return errors

    def get_journal(self, url):
        import requests
        import json
        apitoken = self.preferences.get_key('apitoken')
        headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
        url = url[:-1] if url.endswith('/') else url
        url = url + '?fields=name'
        try:
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                if 'name' in r:
                    return r['name']
            else:
                logging.getLogger('maskgen').error("Unable to connect to service: {}".format(response.text))
        except Exception as e:
            logging.getLogger('maskgen').critical("Cannot reach external service " + url)
            logging.getLogger('maskgen').error(str(e))
        return url

    def test(self):
        import requests
        url = self.preferences.get_key('apiurl')
        apitoken = self.preferences.get_key('apitoken')
        if url is None:
            return "External Service URL undefined"
        baseurl = url
        try:
            url = url[:-1] if url.endswith('/') else url
            headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
            url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
            data = '{ "file_name": {"type": "exact", "value": "' + 'test' + '" }}'
            response = requests.post(url, data=data, headers=headers,timeout=2)
            if response.status_code != requests.codes.ok:
                return "Error calling external service {} : {}".format(baseurl, str(response.content))
        except Exception as e:
            return "Error calling external service: {} : {}".format(baseurl, str(e.message))
        return None

    def get_journal_exporttime(self, journalname):
        """
        :param journalname:
        :return:
        """
        import requests
        import json
        url = self.preferences.get_key('apiurl')
        apitoken = self.preferences.get_key('apitoken')
        if url is None:
            logging.getLogger('maskgen').critical('Missing external service URL.  Check settings')
            return []
        try:
            url = url[:-1] if url.endswith('/') else url
            headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}

            url = url + "/journals/filters/?fields=journal"
            data = '{ "name": { "type": "exact", "value": "' + journalname + '" }}'
            response = requests.post(url, data=data, headers=headers, timeout=2)
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                if 'results' in r:
                    for item in r['results']:
                        return item["journal"]["graph"]["exporttime"]
            else:
               raise EnvironmentError("Unable to connect to service: {}".format(response.text))

        except Exception as e:
            logging.getLogger('maskgen').error("Error calling external service: " + str(e))
            raise EnvironmentError("Cannot reach external Browser to validate export time of journal")

    def get_media_file(self,filename):
        import requests
        import json
        apitoken = self.preferences.get_key('apitoken')
        url = self.preferences.get_key('apiurl')
        if url is None:
            logging.getLogger('maskgen').critical('Missing external service URL. Check system settings.')
            raise EnvironmentError('Non URL Available')
        try:
            url = url[:-1] if url.endswith('/') else url
            headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
            url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
            data = '{ "file_name": {"type": "exact", "value": "' + filename + '" }}'
            logging.getLogger('maskgen').info('checking external service APIs for ' + filename)
            response = requests.post(url, data=data, headers=headers,timeout=2)
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                if 'results' in r:
                    result = []
                    for item in r['results']:
                        info = {}
                        result.append(info)
                        if item['manipulation_journal'] is not None and \
                                        len(item['manipulation_journal']) > 0:
                            info['manipulation_journal'] = self.get_journal(item['manipulation_journal'])
                        info['high_provenance'] = item['high_provenance']
                    return result
            else:
                logging.getLogger('maskgen').error("Unable to connect to service: {}".format(response.text))
                logging.getLogger('maskgen').info("URL: " + url)
                raise ValueError(response.text)
        except Exception as e:
            logging.getLogger('maskgen').error("Error calling external service: " + str(e))
            logging.getLogger('maskgen').info("URL: " + url)
            logging.getLogger('maskgen').critical("Cannot reach external service")
            raise EnvironmentError(url)
        return []


ValidationAPI.register(ValidationBrowserAPI)