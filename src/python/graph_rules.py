from software_loader import getOperations,SoftwareLoader,getOperation
from datetime import datetime

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
  edge = graph.get_edge(frm,to)
  versionResult= checkVersion(edge, op,graph,frm,to)
  mandatoryResult= checkMandatory(edge, op,graph,frm,to)
  result = []
  if versionResult is not  None:
    result.append(versionResult)
  if mandatoryResult is not  None:
    result.extend(mandatoryResult)
  return result


def checkMandatory(edge,op,graph,frm,to):
  opObj = getOperation(op)
  if opObj is None:
    return [op + ' is not a valid operation'] if op != 'Donor' else []
  args = edge['arguments'] if 'arguments' in edge  else []
  missing = [param for param in opObj.mandatoryparameters if (param not in args or len(args[param])== 0) and param == 'inputmask']
  if 'inputmaskname' in opObj.mandatoryparameters and ('inputmaskname' not in edge or len(edge['inputmaskname']) == 0):
    missing.append('inputmask')
  return [('Mandatory parameter ' + m + ' is missing') for m in missing]

def checkVersion(edge,op,graph,frm,to):
  global sloader
  if op == 'Donor':
    return None
  if 'softwareName' in edge and 'softwareVersion' in edge:
    sname = edge['softwareName']
    sversion = edge['softwareVersion']
    if sversion not in sloader.get_versions(sname):
      return sversion + ' not in approved set for software ' + sname
  return None

def setup():
  ops = getOperations()
  for op,data in ops.iteritems():
    set_rules(op,data.rules)

def set_rules(op,ruleNames):
  global rules
  rules[op] = [globals().get(name) for name in ruleNames if len(name) > 0]

def checkForDonor(graph,frm,to):
   pred = graph.predecessors(to)
   if len(pred) < 2:
     return 'donor image missing'
   return None

def warpMethodCheckRule(graph,frm,to):
   edge = graph.get_edge(frm,to)
   method = getValue(edge,'arguments.Method')
   if method and method not in ['Whole Frames', 'Frame Mix' and 'Pixel Motion']:
     return 'Wrap method is invalid.  Should be one of "Whole Frames", "Frame Mix" and "Pixel Motion"'

def vectorDetailRule(graph,frm,to):
   edge = graph.get_edge(frm,to)
   detail = getValue(edge,'arguments.Vector Detail')
   try:
     if detail and int(detail) < 0:
       raise ValueError(str(detail))
   except ValueError:
      return 'Vector Detail is required to be an integer greater than 0'
   return None

def timeResolutionCheck(graph,frm,to):
   edge = graph.get_edge(frm,to)
   detail = getValue(edge,'arguments.Time Resolution')
   try:
     if detail and int(detail) < 0:
       raise ValueError(str(detail))
   except ValueError:
      return 'Time Resolution is required to be an integer greater than 0. The value should be greater than the frame rate.'
   return None

def maxDisplacementCheck(graph,frm,to):
   edge = graph.get_edge(frm,to)
   detail = getValue(edge,'arguments.Max Displacement Time')
   try:
     if detail and int(detail) < 0:
       raise ValueError(str(detail))
   except ValueError:
      return 'Max Displacement Time is required to be an integer greater than 0'
   return None

def adjustTimeRule(graph,frm,to):
   edge = graph.get_edge(frm,to)
   detail = getValue(edge,'arguments.Adjust Time By')
   try:
     if detail and (int(detail) < 0 or int(detail) > 100):
       raise ValueError(str(detail))
   except ValueError:
      return 'Adjust Time By is required to be an integer value from 0 to 100'
   return None

def timeCheckRule(graph,frm,to):
   edge = graph.get_edge(frm,to)
   st = None
   et = None
   try:
     tv = getValue(edge,'arguments.Start Time')
     if tv:
        st = datetime.strptime(tv, '%H:%M:%S.%f')  
     tv = getValue(edge,'arguments.Stop Time')
     if tv:
        et = datetime.strptime(tv, '%H:%M:%S.%f')
   except ValueError:
     return "Invalid Start and Stop Time formats. Use HH:MI:SS.microseconds"
   if st and et and st > et:
     return "Start Time occurs after Stop Time"

def checkLengthSame(graph,frm,to):
   """ the length of video should not change 
   """
   edge = graph.get_edge(frm,to)
   durationChangeTuple = getValue(edge,'metadatadiff[0].duration')
   if durationChangeTuple is not None and durationChangeTuple[0] == 'change':
     return "Length of video has changed"

def checkLengthSmaller(graph,frm,to):
   edge = graph.get_edge(frm,to)
   durationChangeTuple = getValue(edge,'metadatadiff[0].duration')
   if durationChangeTuple is None or \
      (durationChangeTuple[0] == 'change' and durationChangeTuple[1] < durationChangeTuple[2]):
     return "Length of video is not shorter"

def checkLengthBigger(graph,frm,to):
   edge = graph.get_edge(frm,to)
   durationChangeTuple = getValue(edge,'metadatadiff[0].duration')
   if durationChangeTuple is None or \
      (durationChangeTuple[0] == 'change' and durationChangeTuple[1] > durationChangeTuple[2]):
     return "Length of video is not longer"

def checkDonor(graph,frm,to):
   pred = graph.predecessors(to)
   if len(pred) < 2:
     return 'donor must be associated with a image node that has a inbound paste operation'
   return None

def seamCarvingCheck(graph,frm,to):
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

def getValue(obj,path,convertFunction=None):
    """"Return the value as referenced by the path in the embedded set of dictionaries as referenced by an object
        obj is a node or edge
        path is a dictionary path: a.b.c
        convertFunction converts the value

        This function recurses
    """
    if not path:
      return convertFunction(obj) if convertFunction and obj else obj

    current = obj
    part = path
    splitpos = path.find(".")

    if splitpos > 0:
      part = path[0:splitpos]
      path = path[splitpos+1:]
    else:
      path = None

    bpos= part.find('[')
    pos = 0
    if bpos > 0:
      pos = int(part[bpos+1:-1])
      part = part[0:bpos]

    if part in current:
      current = current[part]
      if type(current) is list:
        if bpos>0:
          current = current[pos]
        else:
          result = []
          for item in current:
            v = getValue(item, path,convertFunction)
            if v:
              result.append(v)
          return result
      return getValue(current, path,convertFunction)
    return None
