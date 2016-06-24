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
      loaded[op[0]] = {}
      loaded[op[0]]['function']=plugin.transform
      loaded[op[0]]['operation']=op
   return loaded

def getOperations():
    global loaded
    ops = {}
    for l in loaded.keys():
        op = loaded[l]['operation']
        if not ops.has_key(op[1]):
            ops[op[1]]=[]
        ops[op[1]].append((op[0],op[2]))
    return ops
    
def callPlugin(name,im):
    global loaded
    return loaded[name]['function'](im)
