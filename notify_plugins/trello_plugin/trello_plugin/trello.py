import requests
import json
import os
from maskgen.software_loader import getFileName
from maskgen.maskgen_loader import MaskGenLoader
from maskgen.notifiers import MaskgenNotifer

def factory(loader):
    """
    @type loader: MaskGenLoader
    """
    return TrelloAPI(loader)

class TrelloAPI(MaskgenNotifer):

    loader = None
    """
    @type loader: MaskGenLoader
    """
    def __init__(self,loader):
        """
        :param loader:
        @type loader: MaskGenLoader
        """
        self.loader = loader
        fileName = getFileName('trello.json',path='trello_plugin')
        with open(fileName, 'r') as f:
            self.loaded_config = json.load(f)

    def post_to_trello(self,url,**data):
        """
        :param url:
        :return:
        """
        url = self.loaded_config['url'] + url
        params = dict(key=self.loader.get_key('trelloapikey'),
                      token=self.loader.get_key('trelloapitoken'))
        for k, v in data.iteritems():
            params[k] = v
        resp = requests.post(url, params=params)
        if resp.status_code == requests.codes.ok:
            return json.loads(resp.content)
        return None

    def put_to_trello(self,url,**data):
        """
        :param url:
        :return:
        """
        url = self.loaded_config['url'] + url
        params = dict(key=self.loader.get_key('trelloapikey'),
                      token=self.loader.get_key('trelloapitoken'))
        for k, v in data.iteritems():
            params[k] = v
        resp = requests.post(url, params=params)
        if resp.status_code == requests.codes.ok:
            return json.loads(resp.content)
        return None

    def get_from_trello(self,url, **data):
        """
        :param url:
        :return:
        """
        url = self.loaded_config['url'] + url
        params = dict(key=self.loader.get_key('trelloapikey'),
                      token=self.loader.get_key('trelloapitoken'))
        for k,v in data.iteritems():
            params[k] = v
        resp = requests.get(url,params=params)
        if resp.status_code == requests.codes.ok:
            return  json.loads(resp.content)
        return None

    def get_board_id_by_name(self, name):
        r = self.get_from_trello(self.loaded_config['boards'].format(trelloapiusername=self.loader.get_key('trelloapiusername')),fields='name')
        for item in r:
            if name == item['name']:
                return item['id']
        return ''

    def get_list_id_by_name(self, board,name,create=False):
        boardid = self.get_board_id_by_name(board)
        r = self.get_from_trello(
            self.loaded_config['lists'].format(boardid=boardid),
            fields='name')
        for item in r:
            if name == item['name']:
                return item['id']
        if create:
            r = self.post_to_trello(self.loaded_config['lists'].format(boardid=boardid), name=name)
            return r['id'] if r is not None else ''
        print ''


    def get_card_id_by_name(self, board, listname, cardname,create=False):
        listid = self.get_list_id_by_name(board,listname,create=create)
        r = self.get_from_trello(
            self.loaded_config['cards'].format(listid=listid),
            fields='name,closed')
        for item in r:
            if cardname == item['name']:
                return (item['id'], item['closed'])
        if create:
            r = self.post_to_trello(
                self.loaded_config['cards'].format(listid=listid),
                name=cardname)
            return (r['id'],False) if r is not None else None
        return None

    def get_or_create_label(self,board,name):
        boardid = self.get_board_id_by_name(board)
        r = self.get_from_trello(
            self.loaded_config['labels'].format(boardid=boardid),
            fields='name')
        for item in r:
            if name == item['name']:
                return item['id']
        r = self.post_to_trello(self.loaded_config['labels'].format(boardid=boardid), name=name, color='blue')
        return r['id'] if r is not None else ''

    def add_label_to_card(self,board,cardid, label):
        labelid = self.get_or_create_label(board, label)
        #self.get_from_trello()
        self.post_to_trello(
            self.loaded_config['label'].format(cardid=cardid),
            value=labelid)

    def update_status_to_card(self, board, listname, cardname, comment, label, create=False):
        cardinfo = self.get_card_id_by_name(board,listname,cardname,create=create)
        if cardinfo:
            if cardinfo[1]:
                self.put_to_trello(
                    self.loaded_config['closed'].format(cardid=cardinfo[0]),
                    value=False)

            self.post_to_trello(
                self.loaded_config['comment'].format(cardid=cardinfo[0]),
                text=comment)

            self.add_label_to_card(board,cardinfo[0],label)

    def update_journal_status(self,journalid,comment):
        self.update_status_to_card(self.loaded_config['board.name'],
                                           self.loader.get_key('username'),
                                           journalid, # card name
                                           comment,   # comment
                                           self.loaded_config['label.reviewname'],
                                           create=True)
