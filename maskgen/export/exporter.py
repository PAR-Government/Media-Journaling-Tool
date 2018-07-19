
import os
import boto3
from boto3.s3.transfer import S3Transfer, TransferConfig
from maskgen.tool_set import S3ProgressPercentage
import logging


def startUpload(name, location, path):
    logger = filewriter(os.path.join(os.path.expanduser('~'), 'ExportLogs', name + '.txt'))
    try:
        config = TransferConfig()
        s3 = S3Transfer(boto3.client('s3', 'us-east-1'), config)
        BUCKET = location.split('/')[0].strip()
        DIR = location[location.find('/') + 1:].strip()
        logging.getLogger('maskgen').info('Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1])
        DIR = DIR if DIR.endswith('/') else DIR + '/'
        s3.upload_file(path, BUCKET, DIR + os.path.split(path)[1], callback=S3ProgressPercentage(path, logger))
        os.remove(path)
    except Exception:
        logger('Failed')
        return []
    logger('Done')
    return []

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


