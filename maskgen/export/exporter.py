import maskgen.scenario_model
import maskgen.image_graph
import os


def start(projectfile, s3bucket):
    project = maskgen.scenario_model.loadProject(projectfile)
    logger = filewriter(os.path.join('.','ExportLogs',project.getName() + '.txt'))
    try:
        project.exporttos3(s3bucket,log=logger)
    except Exception:
        logger('Failed')
    logger('Done')



class filewriter():
    def __init__(self, fp):
        self.fileName = fp
        file = open(fp, 'w+')
        file.write(str(os.getpid()))
        file.close()

    def __call__(self, txt):
        file = open(self.fileName, 'a')
        file.write(txt+'\n')
        file.close()


