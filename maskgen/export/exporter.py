import maskgen.scenario_model
import maskgen.image_graph
import sys
import os

def main():
	project = maskgen.scenario_model.loadProject(sys.argv[1])
	project.exporttos3()

class filewriter():
	def __init__(self,fp):
		self.file = open(fp,'w+')
		self.file.write(str(os.getpid()))

	def __call__(self, txt):
		self.file.write(txt)