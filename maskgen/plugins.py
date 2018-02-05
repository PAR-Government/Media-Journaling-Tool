import sys
import os
import json
import subprocess
import logging
import tarfile
import importlib
import traceback

"""
Manage and invoke all JT plugins that support operations on node media (images, video and audio)
"""

MainModule = "__init__"

loaded = None

def installPlugin(zippedFile):
    global loaded
    def extract_archive(fname, dir):
        try:
            archive = tarfile.open(fname, "r:gz", errorlevel=2)
        except Exception as e:
            try:
                archive = tarfile.open(fname, "r", errorlevel=2)
            except Exception as e:
                if archive is not None:
                    archive.close()
                logging.getLogger('maskgen').critical(
                    "Cannot open archive {}; it may be corrupted ".format(fname))
                logging.getLogger('maskgen').error(str(e))
                return []
        pluginnames = set([name.split('/')[0] for name in archive.getnames()])
        archive.extractall(dir)
        archive.close()
        return list(pluginnames)

    pluginFolders = [os.path.join('.', "plugins"), os.getenv('MASKGEN_PLUGINS', 'plugins')]
    pluginFolders.extend([os.path.join(x, 'plugins') for x in sys.path if 'maskgen' in x])
    for folder in pluginFolders:
        if os.path.exists(folder):
            for name in  extract_archive(zippedFile, folder):
                location = os.path.join(folder, name)
                info = _findPluginModule(location)
                if info is not None:
                    _loadPluginModule(info,name,loaded)
            break

def _loadPluginModule(info,name,loaded):
    logging.getLogger('maskgen').info("Loading plugin " + name)
    try:
        plugin = __import__(info)
        op = plugin.operation()
        loaded[name] = {}
        loaded[name]['function'] = plugin.transform
        loaded[name]['operation'] = op
        loaded[name]['suffix'] = plugin.suffix() if hasattr(plugin, 'suffix') else None
    except Exception as e:
        logging.getLogger('maskgen').error("Failed loading plugin " + name + ": " + str(e))
    #finally:
    #    info[0].close()

def _findPluginModule(location):
    if not os.path.isdir(location) or not MainModule + ".py" in os.listdir(location):
        return None
    return os.path.basename(location) #imp.find_module(MainModule, [location])

def getPlugins(reload=False,customFolders=[]):
    plugins = {}
    pluginFolders = [os.path.join('.', "plugins"), os.getenv('MASKGEN_PLUGINS', 'plugins')]
    pluginFolders.extend([os.path.join(x,'plugins') for x in sys.path if 'maskgen' in x])
    pluginFolders.extend(customFolders)
    pluginFolders = set([os.path.abspath(f) for f in pluginFolders])
    for folder in pluginFolders:
        if os.path.exists(folder):
            if folder not in sys.path:
                sys.path.append(folder)
            possibleplugins = os.listdir(folder)
            customfolder = os.path.join(folder, 'Custom')
            customplugins = os.listdir(customfolder) if os.path.exists(customfolder) else []
            for i in possibleplugins:
                if i in plugins:
                    continue
                if i == 'Custom':
                    continue
                location = os.path.join(folder, i)
                mod = _findPluginModule(location)
                if mod is not None:
                   plugins[i] = {"info": mod}
            for j in customplugins:
                location = os.path.join(folder, 'Custom', j)
                plugins[os.path.splitext(j)[0]] = {"custom": location}
    return plugins

def loadCustom(plugin, path):
    """
    loads a custom plugin
    """
    global loaded
    logging.getLogger('maskgen').info("Loading plugin " + plugin)
    try:
        with open(path) as jfile:
            data = json.load(jfile)
        loaded[plugin] = {}
        loaded[plugin]['function'] = 'custom'
        loaded[plugin]['operation'] = data['operation']
        loaded[plugin]['command'] = data['command']
        loaded[plugin]['group'] = None
        loaded[plugin]['mapping'] = data['mapping'] if 'mapping' in data else None
        loaded[plugin]['suffix'] = data['suffix'] if 'suffix' in data else None
    except Exception as e:
        logging.getLogger('maskgen').error("Failed to load plugin {}: {} ".format(plugin, str(e)))


def pluginSummary():
    import csv
    csv.register_dialect('unixpwd', delimiter=',', quoting=csv.QUOTE_MINIMAL)
    loaded = loadPlugins()
    with open('plugin.csv','w') as fp:
        csv_fp = csv.writer(fp)
        for plugin_name,plugin_def in loaded.iteritems():
            args = plugin_def['operation']['arguments'] if 'arguments' in plugin_def['operation'] else {}
            args = {} if args is None else args
            csv_fp.writerow([plugin_name,plugin_def['operation']['name'],
                         plugin_def['operation']['category'],
                         plugin_def['operation']['software'],
                         plugin_def['operation']['description'],
                         'yes' if 'inputmaskname' in args else 'no'])


def loadPlugins(reload=False, customFolders=[]):
   global loaded

   if loaded is not None and not reload:
       return loaded

   loaded = {}
   ps = getPlugins(customFolders=customFolders)
   for i in ps.keys():
      if 'custom' in ps[i]:
          path = ps[i]['custom']
          loadCustom(i, path)
      else:
          _loadPluginModule(ps[i]['info'],i,loaded)

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
    if loaded is None:
        loaded = loadPlugins()
    if name not in loaded:
        raise ValueError('Request plugined not found: ' + str(name))
    if loaded[name]['function'] == 'custom':
        return runCustomPlugin(name, im, source, target, **kwargs)
    else:
        try:
            return loaded[name]['function'](im,source,target,**kwargs)
        except Exception as e:
            logging.getLogger('maskgen').error('Plugin {} failed with {} for arguments {}'. format(name, str(e), str(kwargs)))
            logging.getLogger('maskgen').error(' '.join(traceback.format_stack()))
            raise e

def runCustomPlugin(name, im, source, target, **kwargs):
    global loaded
    import copy
    if name not in loaded:
        raise ValueError('Request plugined not found: ' + str(name))
    commands = copy.deepcopy(loaded[name]['command'])
    mapping = copy.deepcopy(loaded[name]['mapping'])
    executeOk = False
    try:
        for k, command in commands.items():
            if sys.platform.startswith(k):
                executeWith(command, im, source, target, mapping, **kwargs)
                executeOk = True
                break
        if not executeOk:
            executeWith(commands['default'], im, source, target, mapping, **kwargs)
    except Exception as e:
        logging.getLogger('maskgen').error('Plugin {} failed with {} for arguments {}'.format(name,str(e), str(kwargs)))
        raise e
    return None, None

def executeWith(executionCommand, im, source, target, mapping, **kwargs):
    shell=False
    if executionCommand[0].startswith('s/'):
        executionCommand[0] = executionCommand[0][2:]
        shell = True
    kwargs = mapCmdArgs(kwargs, mapping)
    kwargs['inputimage'] = source
    kwargs['outputimage'] = target
    for i in range(len(executionCommand)):
        try:
            executionCommand[i] = executionCommand[i].format(**kwargs)
        except KeyError as e:
            logging.getLogger('maskgen').warn('Argument {} not provided for {}'.format(e.message,executionCommand[0]))
    ret = subprocess.call(executionCommand,shell=shell)
    if ret != 0:
        raise RuntimeError('Plugin {} failed with code {}'.format(executionCommand[0],ret))


def mapCmdArgs(args, mapping):
    import copy
    newargs = copy.copy(args)
    if mapping is not None:
        for key, val in args.iteritems():
            if key in mapping:
                if val not in mapping[key] or mapping[key][val] is None:
                    raise ValueError('Option \"' + str(val) + '\" is not permitted for this plugin.')
                newargs[key] = mapping[key][val]
    return newargs

def findPlugin(pluginName):
    import errno
    pluginFolders = [os.path.join('.', "plugins"), os.getenv('MASKGEN_PLUGINS', 'plugins')]
    pluginFolders.extend([os.path.join(x,'plugins') for x in sys.path if 'maskgen' in x])
    for parent in pluginFolders:
        if not os.path.exists(parent):
            continue
        for f in os.listdir(parent):
            if f == pluginName:
                return os.path.join(parent, f)
                
    raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), pluginName)
