import sys
import imp
import os
import json
import subprocess
import logging

MainModule = "__init__"

loaded = None

def getPlugins():
    plugins = {}
    pluginFolders = [os.path.join('.', "plugins"), os.getenv('MASKGEN_PLUGINS', 'plugins')]
    pluginFolders.extend([os.path.join(x,'plugins') for x in sys.path if 'maskgen' in x])
    for folder in pluginFolders:
        if os.path.exists(folder):
            possibleplugins = os.listdir(folder)
            customfolder = os.path.join(folder, 'Custom')
            customplugins = os.listdir(customfolder) if os.path.exists(customfolder) else []
            for i in possibleplugins:
                if i in plugins:
                    continue
                if i == 'Custom':
                    continue
                location = os.path.join(folder, i)
                if not os.path.isdir(location) or not MainModule + ".py" in os.listdir(location):
                    continue
                info = imp.find_module(MainModule, [location])
                plugins[i] = {"info": info}

            for j in customplugins:
                location = os.path.join(folder, 'Custom', j)
                plugins[os.path.splitext(j)[0]] = {"custom": location}

    return plugins

def loadPlugin(plugin):
    return imp.load_module(plugin['name'], *plugin["info"])

def loadCustom(plugin, path):
    """
    loads a custom plugin
    """
    global loaded
    logging.getLogger('maskgen').info("Loading plugin " + plugin)
    with open(path) as jfile:
        data = json.load(jfile)
    loaded[plugin] = {}
    loaded[plugin]['function'] = 'custom'
    loaded[plugin]['operation'] = data['operation']
    loaded[plugin]['command'] = data['command']
    loaded[plugin]['group'] = None
    loaded[plugin]['mapping'] = data['mapping'] if 'mapping' in data else None
    loaded[plugin]['suffix'] = data['suffix'] if 'suffix' in data else None

def loadPlugins():
   global loaded
   if loaded is not None:
       return loaded

   loaded = {}
   ps = getPlugins() 
   for i in ps.keys():
      if 'custom' in ps[i]:
          path = ps[i]['custom']
          loadCustom(i, path)
      else:
          logging.getLogger('maskgen').info("Loading plugin " + i)
          plugin = imp.load_module(MainModule, *ps[i]["info"])
          loaded[i] = {}
          loaded[i]['function'] = plugin.transform
          loaded[i]['operation'] = plugin.operation()
          # loaded[i]['arguments'] = plugin.args()
          loaded[i]['suffix'] = plugin.suffix() if hasattr(plugin,'suffix') else None
   return loaded

def getOperations(fileType=None):
    global loaded
    ops = {}
    for l in loaded.keys():
        if 'operation' not in loaded[l]:
            logging.getLogger('maskgen').error('Invalid plugin {}'.format(l))
            continue
        transitions = loaded[l]['operation']['transitions'] if 'transitions' in loaded[l]['operation'] else []
        transitions = [t.split('.')[0] for t in transitions]
        if fileType is None or fileType in transitions:
            ops[l] = loaded[l]
    return ops


def getPreferredSuffix(name):
    global loaded
    return loaded[name]['suffix'] if 'suffix' in loaded[name] else None

def getOperation(name):
    global loaded
    if name not in loaded:
        logging.getLogger('maskgen').warning('Requested plugin not found: ' + str(name))
        return None
    return loaded[name]['operation']

def callPlugin(name,im,source,target,**kwargs):
    global loaded
    if name not in loaded:
        raise ValueError('Request plugined not found: ' + str(name))
    if loaded[name]['function'] == 'custom':
        return runCustomPlugin(name, im, source, target, **kwargs)
    else:
        return loaded[name]['function'](im,source,target,**kwargs)

def runCustomPlugin(name, im, source, target, **kwargs):
    global loaded
    import copy
    if name not in loaded:
        raise ValueError('Request plugined not found: ' + str(name))
    commands = copy.deepcopy(loaded[name]['command'])
    mapping = copy.deepcopy(loaded[name]['mapping'])
    executeOk = False
    for k, command in commands.items():
        if sys.platform.startswith(k):
            executeWith(command, im, source, target, mapping, **kwargs)
            executeOk = True
            break
    if not executeOk:
        executeWith(commands['default'], im, source, target, mapping, **kwargs)
    return None, None

def executeWith(executionCommand, im, source, target, mapping, **kwargs):
    shell=False
    if executionCommand[0].startswith('s/'):
        executionCommand[0] = executionCommand[0][2:]
        shell = True
    kwargs = mapCmdArgs(kwargs, mapping)
    for i in range(len(executionCommand)):
        if executionCommand[i] == '{inputimage}':
            executionCommand[i] = source
        elif executionCommand[i] == '{outputimage}':
            executionCommand[i] = target

        # Replace bracketed text with arg
        else:
            executionCommand[i] = executionCommand[i].format(**kwargs)
    subprocess.call(executionCommand,shell=shell)

def mapCmdArgs(args, mapping):
    if mapping is not None:
        for key, val in args.iteritems():
            if key in mapping:
                if val not in mapping[key] or mapping[key][val] is None:
                    raise ValueError('Option \"' + str(val) + '\" is not permitted for this plugin.')
                args[key] = mapping[key][val]
    return args
