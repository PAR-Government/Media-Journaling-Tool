from software_loader import getOperations,SoftwareLoader

rules = {}
sloader = SoftwareLoader()

def run_rules(op, graph, frm,to):
  global rules
  if len(rules) == 0:
    setup()
  results = initialCheck(op,graph,frm,to)
  for rule in (rules[op] if op in rules else []):
     res = rule(graph,frm,to)
     if res is not None:
       results.append(res)
  return results

def initialCheck(op,graph,frm,to):
  versionResult= checkVersion(op,graph,frm,to)
  return [] if versionResult is  None else [versionResult]

def checkVersion(op,graph,frm,to):
  global sloader
  edge = graph.get_edge(frm,to)
  if 'softwareName' in edge and 'softwareVersion' in edge:
    sname = edge['softwareName']
    sversion = edge['softwareVersion']
    if sversion not in sloader.get_versions(sname):
      return sversion + ' not in approved set for software ' + sname
  return None

def setup():
  ops = getOperations()
  for op,data in ops.iteritems():
    set_rules(op,data[1:])

def set_rules(op,ruleNames):
  global rules
  rules[op] = [globals().get(name) for name in ruleNames]

def checkForDonor(graph,frm,to):
   pred = graph.predecessors(to)
   if len(pred) < 2:
     return 'donor image missing'
   return None

def checkDonor(graph,frm,to):
   pred = graph.predecessors(to)
   if len(pred) < 2:
     return 'donor must be associated with a image node that has a inbound paste operation'
   return None

def seamCarvingCheck(edge):
   change = getSizeChange(graph,frm,to)
   if change is not None and change[0] != 0 and change[1] != 0:
     return 'seam carving should not alter both dimensions of an image'
   return None

def sizeChanged(graph,frm,to):
   change = getSizeChange(graph,frm,to)
   if change is not None and (change[0] == 0 and change[1] == 0):
     return 'operation should change the size of the image'
   return None

def checkSize(graph,frm,to):
   change = getSizeChange(graph,frm,to)
   if change is not None and (change[0] != 0 or change[1] != 0):
     return 'operation is not permitted to change the size of the image'
   return None
      
def getSizeChange(graph,frm,to):
   edge = graph.get_edge(frm,to)
   change= edge['shape change'] if edge is not None and 'shape change' in edge else None
   if change is not None:
       xyparts = change[1:-1].split(',')
       x = int(xyparts[0].strip())
       y = int(xyparts[1].strip())
       return (x,y)
   return None
