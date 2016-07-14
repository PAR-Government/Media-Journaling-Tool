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
      op = plugin.operation()
      loaded[i] = {}
      loaded[i]['function']=plugin.transform
      loaded[i]['operation']=op
   return loaded

def getOperations():
    global loaded
    ops = {}
    for l in loaded.keys():
        op = loaded[l]['operation']
        ops[l] = op
    return ops
    
def getOperation(name):
    global loaded
    return loaded[name]['operation']

def callPlugin(name,im):
    global loaded
    return loaded[name]['function'](im)
