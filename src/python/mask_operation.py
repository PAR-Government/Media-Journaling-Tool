
def loadOperations(fileName):
    dict={}
    with open(fileName) as f:
        for l in f.readlines():
            columns = l.split(',')
            if (len(columns) > 2):
              category = columns[1].strip()
              if not dict.has_key(category):
                  dict[category] = []
              dict[category].append(columns[0].strip())
    return dict
