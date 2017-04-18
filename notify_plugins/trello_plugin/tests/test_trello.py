import unittest
from trello_plugin.trello import TrelloAPI
from maskgen.maskgen_loader import  MaskGenLoader

class TestToolSet(unittest.TestCase):
    def test_aproject(self):
        api = TrelloAPI(MaskGenLoader())
        api.update_status_to_card('JournalQA','testlist','123','test 123', 'to be removed', create=True)


if __name__ == '__main__':
    unittest.main()
