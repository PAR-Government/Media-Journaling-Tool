import requests
import json
import os
from maskgen.software_loader import getFileName
from maskgen.maskgen_loader import MaskGenLoader
from maskgen.notifiers import MaskgenNotifer
import logging

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

    def _get_logger(self):
        logger = logging.getLogger('TrelloAPI')
        if len(logger.handlers) == 0:
            for handler in logging.getLogger('maskgen').handlers:
                logger.addHandler(handler)
        return logger

    def post_to_trello(self,url,purpose, quiet=False,**data):
        """
        :param url:
        :return:
        """
        url = self.loaded_config['url'] + url
        params = dict(key=self.loaded_config['trelloapikey'],
                      token=self.loader.get_key('trelloapitoken','').strip())
        for k, v in data.iteritems():
            params[k] = v
        resp = requests.post(url, params=params)
        if resp.status_code == requests.codes.ok:
            return json.loads(resp.content)
        if not quiet:
            self._get_logger().error('failed to contact trello service {}: {}'.format(purpose, resp.text))
        return None

    def check_status(self):
        r = self.get_from_trello(
            self.loaded_config['user'],
            'get user name',
            fields='username')
        if r is None:
            return 'Trello user validation failed'
        isMember = self.get_board_membership(self.loaded_config['board.name'])
        if not isMember:
            return 'Access to Board {} failed'.format(self.loaded_config['board.name'])

    def get_properties(self):
        return {"trelloapitoken" : "Trello API Token"}

    def put_to_trello(self,url,purpose, **data):
        """
        :param url:
        :return:
        """
        url = self.loaded_config['url'] + url
        params = dict(key=self.loaded_config['trelloapikey'],
                      token=self.loader.get_key('trelloapitoken',''))
        for k, v in data.iteritems():
            params[k] = v
        resp = requests.post(url, params=params)
        if resp.status_code == requests.codes.ok:
            return json.loads(resp.content)
        self._get_logger().error('failed to contact trello service {}: {}'.format(purpose,resp.text))
        return None

    def get_from_trello(self,url,purpose, **data):
        """
        :param url:
        :return:
        """
        #self._get_logger().info(purpose)
        url = self.loaded_config['url'] + url
        params = dict(key=self.loaded_config['trelloapikey'],
                      token=self.loader.get_key('trelloapitoken',''))
        for k,v in data.iteritems():
            params[k] = v
        resp = requests.get(url,params=params)
        if resp.status_code == requests.codes.ok:
            return  json.loads(resp.content)
        self._get_logger().error('failed to contact trello service {}: {}'.format((url if purpose is None else purpose),resp.text))
        return None

    def get_user_name(self):
        regid = self.loader.get_key('trelloapiusername')
        if regid is not None:
            return regid
        r = self.get_from_trello(
            self.loaded_config['user'],
            'get user name',
            fields='username')
        if r is None:
            self._get_logger().error('failed to Trello username')
        return r['username'] if r is not None else 'unknown_user'

    def get_board_id_by_name(self, name):
        r = self.get_from_trello(self.loaded_config['boards'].format(trelloapiusername=self.get_user_name()),
                                 'get board id of board {}'.format(name),
                                 fields='name')
        if r is not None:
            for item in r:
                if name == item['name']:
                    return item['id']
        self._get_logger().error('Could not find id of board named {}'.format(name))
        return ''

    def get_board_membership(self, name):
        boardid = self.get_board_id_by_name(name)
        r = self.get_from_trello(self.loaded_config['memberships'].format(boardid=boardid),
                                 'find memberships for board {}'.format(name),
                                 filter='me')
        if type(r) == list:
            for i in r:
                if i is not None and 'idMember' in i:
                    return True
            return False
        return r is not None and 'idMember' in r



    def get_list_id_by_name(self, board,name,create=False):
        boardid = self.get_board_id_by_name(board)
        r = self.get_from_trello(
            self.loaded_config['lists'].format(boardid=boardid),
            'get id of list {} in board'.format(name, board),
            fields='name')
        if r is not None:
            for item in r:
                if name == item['name']:
                    return item['id']
        if create:
            r = self.post_to_trello(self.loaded_config['lists'].format(boardid=boardid),
                                    'create list {} on board {}'.format(name, board),
                                    quiet=False,
                                    name=name)
            if r is None:
                self._get_logger().error("Cannot create a list under board {}  with name {}.".format(board,name))
            return r['id'] if r is not None else ''
        return ''


    def get_card_id_by_name(self, board, listname, cardname,create=False):
        listid = self.get_list_id_by_name(board,listname,create=create)
        r = self.get_from_trello(
            self.loaded_config['cards'].format(listid=listid),
            'find card {} within list {} of board {}'.format(cardname,listname,board),
            fields='name,closed')
        if r is not None:
            for item in r:
                if cardname == item['name']:
                    return (item['id'], item['closed'])
        if create:
            r = self.post_to_trello(
                self.loaded_config['cards'].format(listid=listid),
                'create card {} on list {} of board {}'.format(cardname,listname,board ),
                quiet=False,
                name=cardname)
            return (r['id'],False) if r is not None else None
        return None

    def get_or_create_label(self,board,name):
        boardid = self.get_board_id_by_name(board)
        r = self.get_from_trello(
            self.loaded_config['labels'].format(boardid=boardid),
            'get labels on board {}'.format(board),
            fields='name')
        if r is not None:
            for item in r:
                if name == item['name']:
                    return item['id']
        r = self.post_to_trello(self.loaded_config['labels'].format(boardid=boardid),
                                'create label {} on board {}'.format(name,board),
                                quiet=False,
                                name=name,
                                color='blue')
        return r['id'] if r is not None else ''

    def add_label_to_card(self,board,cardid, label):
        labelid = self.get_or_create_label(board, label)
        self.post_to_trello(
            self.loaded_config['label'].format(cardid=cardid),
            'add label {} to card {} on board {}'.format(label, cardid, board),
            quiet=True,
            value=labelid)

    def update_status_to_card(self, board, listname, cardname, comment, labels, create=False):
        cardinfo = self.get_card_id_by_name(board,listname,cardname,create=create)
        if cardinfo:
            if cardinfo[1]:
                self.put_to_trello(
                    self.loaded_config['closed'].format(cardid=cardinfo[0]),
                    'close card {} of list {} on board {}'.format(cardname, listname, board),
                    value=False)

            ok = self.post_to_trello(
                self.loaded_config['comment'].format(cardid=cardinfo[0]),
                'add comment to card {} of list {} on board {}'.format(cardname, listname, board),
                quiet=False,
                text=comment) is not None

            for label in labels:
                self.add_label_to_card(board,cardinfo[0],label)

            return ok
        else:
            return False

    def update_journal_status(self,journalid,user,comment, typeofjournal):
        return self.update_status_to_card(self.loaded_config['board.name'],
                                           user,
                                           journalid, # card name
                                           comment,   # comment
                                           [self.loaded_config['label.reviewname'],typeofjournal],
                                           create=True)
