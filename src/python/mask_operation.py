
def loadOperations(fileName):
    with open(fileName) as f:
        return [x.strip() for x in f.readlines()]
