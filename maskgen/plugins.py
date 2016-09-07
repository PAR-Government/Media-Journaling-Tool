import imp
import os

PluginFolder = "./plugins"
MainModule = "__init__"

loaded = None

def getPlugins():
    plugins = {}
    possibleplugins = os.listdir(PluginFolder)
    for i in possibleplugins:
        location = os.path.join(PluginFolder, i)
        if not os.path.isdir(location) or not MainModule + ".py" in os.listdir(location):
            continue
        info = imp.find_module(MainModule, [location])
        plugins[i]={"info": info}
    return plugins

def loadPlugin(plugin):
    return imp.load_module(plugin['name'], *plugin["info"])

def loadPlugins():
   global loaded
   if loaded is not None:
       return loaded

   loaded = {}
   ps = getPlugins() 
   for i in ps.keys():
      print("Loading plugin " + i)
      plugin = imp.load_module(MainModule, *ps[i]["info"])
      loaded[i] = {}
      loaded[i]['function']=plugin.transform
      loaded[i]['operation']=plugin.operation()
      loaded[i]['arguments']=plugin.args()
      loaded[i]['suffix']=plugin.suffix() if hasattr(plugin,'suffix') else None
   return loaded

def getOperations():
    global loaded
    ops = {}
    for l in loaded.keys():
        ops[l] = loaded[l]
    return ops

# return list of tuples, name and default value (which can be None)
def getArguments(name):
    global loaded
    return loaded[name]['arguments']

def getPreferredSuffix(name):
    global loaded
    return loaded[name]['suffix']

def getOperationNames(noArgs=False):
    global loaded
    if not noArgs:
      return loaded.keys()
    result = []
    for k,v in loaded.iteritems():
      if v['arguments'] is None or len(v['arguments'])==0:
        result.append(k)
    return result
    
def getOperation(name):
    global loaded
    return loaded[name]['operation']

def callPlugin(name,im,source,target,**kwargs):
    global loaded
    return loaded[name]['function'](im,source,target,**kwargs)
