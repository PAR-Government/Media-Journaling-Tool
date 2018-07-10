
import maskgen.image_graph
import os


def startExporter(projectfile, s3bucket, tempdir, additionalmessage):
    import maskgen.scenario_model

    project = maskgen.scenario_model.loadProject(projectfile)
    logger = filewriter(os.path.join(os.path.expanduser('~'),'ExportLogs',project.getName() + '.txt'))
    try:
        project.exporttos3(s3bucket,log=logger,tempdir=tempdir, additional_message=additionalmessage)
    except Exception:
        logger('Failed')
    logger('Done')



class filewriter():
    def __init__(self, fp):
        if not os.path.exists(os.path.split(fp)[0]):
            os.mkdir(os.path.split(fp)[0])
        self.fileName = fp
        file = open(fp, 'w+')
        file.write(str(os.getpid()) + '\n')
        file.close()

    def __call__(self, txt):
        file = open(self.fileName, 'a')
        file.write(txt+'\n')
        file.close()


