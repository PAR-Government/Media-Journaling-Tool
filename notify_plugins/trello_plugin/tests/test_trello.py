import unittest
from trello_plugin.trello import TrelloAPI
from maskgen.maskgen_loader import  MaskGenLoader

class TestToolSet(unittest.TestCase):

    def test_aproject(self):
        api = TrelloAPI(MaskGenLoader())
        api.update_status_to_card('JournalQA','testlist','123','test 123\n test 4567', ['to be removed','image'], create=True)


    def test_check(self):
      api = TrelloAPI(MaskGenLoader())
      self.assertTrue(api.check_status())

if __name__ == '__main__':
    unittest.main()
