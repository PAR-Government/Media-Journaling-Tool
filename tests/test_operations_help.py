import unittest
from test_support import TestSupport
import json
import requests
import os
from pptx import Presentation



class TestOperationsHelp(TestSupport):
    def test_operations_help(self):

        downloadLink = "https://s3.amazonaws.com/medifor/browser/journal/JournalingToolOperationsDictionary.pptx"
        powerpointPlace = self.locateFile("resources/operationSlides.pptx")

        r = requests.get(downloadLink)
        with open(powerpointPlace, 'wb+') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
        fd.close()

        imgLinker = self.locateFile("resources\help\image_linker.json")
        operations = self.locateFile("resources\operations.json")

        prs = Presentation(powerpointPlace)
        prs.save('Operations.pptx')
        self.addFileToRemove('Operations.pptx')

        slide = len(prs.slides)
        print 'Number of slides gotten from online: ' + str(slide)

        jtLocation = '../resources/help/operationSlides'
        path, dirs, slides = next(os.walk(jtLocation))
        print "JT Slides: " + str(len(slides))


        with open(imgLinker) as f:
            data = json.load(f)
        with open(operations) as f2:
            opo = json.load(f2)

        images = set()
        missing = []
        for d in opo["operations"]:
            o = d["name"]
            if o not in data["operation"] or len(data["operation"][o]["images"]) == 0 or data["operation"][o]["images"][0] == "":
                missing.append(o)
            else:
                for i in data["operation"][o]["images"]:
                    images.add(i)
                data["operation"].pop(o)

        self.assertTrue(missing==[], "Missing is not empty " + str(missing))
        self.assertTrue(slide == len(slides), "Slides Online doesn't match with the number of slides in the JT")
        self.assertTrue(len(data["operation"]) == 0, "There are extra operation(s) in the help section: " +
                        ", ".join(data["operation"].keys()))

        self.remove_files()

    def test_semantic_group_slides(self):
        downloadLink = "https://s3.amazonaws.com/medifor/browser/journal/SemanticGroups.pptx"
        powerpointPlace = self.locateFile("resources/semanticGroups.pptx")

        r = requests.get(downloadLink)
        with open(powerpointPlace, 'wb+') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
        fd.close()

        imgLinker = self.locateFile("resources\help\image_linker.json")
        groups = self.locateFile("resources\project_properties.json")

        prs = Presentation("../resources/SemanticGroups.pptx")
        prs.save('Operations2.pptx')
        self.addFileToRemove('Operations2.pptx')

        slide = len(prs.slides)
        print 'Number of slides gotten from online: ' + str(slide)

        jtLocation = '../resources/help/semanticSlides'
        path, dirs, slides = next(os.walk(jtLocation))
        print "JT Semantic Slides: " + str(len(slides))
        self.assertTrue(slide == len(slides), "Number of Slides online doesn't match number of slides in the JT")


        with open(imgLinker) as f:
            data = json.load(f)
        with open(groups) as f2:
            semGroups = json.load(f2)
        semanticGroups = []
        for d in semGroups["properties"]:
            try:
                if d["semanticgroup"]:
                    semanticGroups.append(d)
            except:
                pass

        images = set()
        missing = []
        for d in semanticGroups:
            g = d["description"]
            if g not in data["semanticgroup"] or len(data["semanticgroup"][g]["images"]) ==0 or data["semanticgroup"][g]["images"][0] =="":
                missing.append(g)
            else:
                for i in data["semanticgroup"][g]["images"]:
                    images.add(i)
                data["semanticgroup"].pop(g)

        self.assertTrue(missing == [], "Missing is not empty " + str(missing))
        self.assertTrue(len(data["semanticgroup"]) == 0, "There are extra operation(s) in the help section")

        self.remove_files()
        

if __name__ == '__main__':
    unittest.main()
