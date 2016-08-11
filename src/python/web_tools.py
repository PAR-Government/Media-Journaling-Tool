
# tools for assisting with S3 and HTTP functionality

def loadS3(values):
  import boto3
  print 'Download operations and software via S3'
  s3 = boto3.client('s3','us-east-1')
  BUCKET = values[0][0:values[0].find('/')]
  DIR=values[0][values[0].find('/')+1:]
  s3.download_file( BUCKET,DIR + "/operations.json", "operations.json")
  s3.download_file( BUCKET,DIR + "/software.csv", "software.csv")

def loadHTTP(values):
    import requests
    print 'Download operations and software via HTTP'
    head = {}
    for p in range(1, len(values)):
        name = values[p].split(':')[0].strip()
        val = values[p].split(':')[1].strip()
        head[name]=val
    r = requests.get(values[0] + '/operations.json',headers=head)
    if r.status_code < 300:
      with open('operations.json', 'w') as f:
          f.write(r.content)
    r = requests.get(values[0] + '/software.csv',headers=head)
    if r.status_code < 300:
      with open('software.csv', 'w') as f:
          f.write(r.content)