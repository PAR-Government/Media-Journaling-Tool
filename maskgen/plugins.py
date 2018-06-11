import json
import logging
import os
import subprocess
import sys
import tarfile
import traceback
import copy

import config
from maskgen.ioc.registry import IoCComponent, Method, broker

"""
Manage and invoke all JT plugins that support operations on node media (images, video and audio)
"""

MainModule = "__init__"

def installPlugin(zippedFile):
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

    loaded = config.global_config.get('plugins', PluginManager({}))
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

class EchoInterceptor:
    def __init__(self, provided_broker):
        provided_broker.register('PluginManager', self)

    def _callPlugin(self, definition, im, source, target, **kwargs):
        return None,None

class PluginCaller:

    def __init__(self,provided_broker):
        provided_broker.register('PluginManager', self)

    def _callPlugin(self, definition, im, source, target, **kwargs):
        if definition['function'] == 'custom':
            return _runCustomPlugin(definition, im, source, target, **kwargs)
        else:
            return definition['function'](im, source, target, **kwargs)


class PluginManager:
    caller = IoCComponent('PluginManager', Method('_callPlugin'))

    def __init__(self,plugins={}):
        self.plugins=plugins
        #default
        PluginCaller(broker)

    def getBroker(self):
        return broker

    def getPreferredSuffix(self,name,filetype=None):
        name=name.split('::')[0]
        loaded = self.plugins
        if 'suffix' in loaded[name]:
            suffix = loaded[name]['suffix']
        if suffix is not None:
            if type(suffix) == dict and filetype is not None:
                return suffix[filetype]
            return suffix
        return None

    def getOperations(self,fileType=None):
        ops = {}
        loaded = self.plugins
        for l in loaded.keys():
            if 'operation' not in loaded[l]:
                logging.getLogger('maskgen').error('Invalid plugin {}'.format(l))
                continue
            transitions = loaded[l]['operation']['transitions'] if 'transitions' in loaded[l]['operation'] else []
            transitions = [t.split('.')[0] for t in transitions]
            if len(transitions) == 0:
                continue
            if fileType is None or fileType in transitions:
                ops[l] = loaded[l]
        return ops

    def getOperation(self,name):
        loaded = self.plugins
        if name not in loaded:
            logging.getLogger('maskgen').warning('Requested plugin not found: ' + str(name))
            return None
        return loaded[name]['operation']

    def callPlugin(self,name,im,source,target,**kwargs):
        loaded = self.plugins
        if name not in loaded:
            raise ValueError('Request plugined not found: ' + str(name))
        try:
            return self._callPlugin(loaded[name],im, source, target, **kwargs)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace = traceback.format_exception(exc_type, exc_value, exc_traceback)
            logging.getLogger('maskgen').error(
                'Plugin {} failed with {} for arguments {}'.format(name, str(e), str(kwargs)))
            logging.getLogger('maskgen').error(' '.join(trace))
            raise e

    def _callPlugin(self, definition, im, source, target, **kwargs):
        return self.caller(definition, im, source, target, **kwargs)

    def loadCustom(self,name, path):
        """
        loads a custom plugin
        """
        logging.getLogger('maskgen').info("Loading plugin " + name)
        try:
            with open(path) as jfile:
                data = json.load(jfile)
                self.plugins[name] = {}
                self.plugins[name]['function'] = 'custom'
                self.plugins[name]['operation'] = data['operation']
                self.plugins[name]['command'] = data['command']
                self.plugins[name]['group'] = None
                self.plugins[name]['mapping'] = data['mapping'] if 'mapping' in data else None
                self.plugins[name]['suffix'] = data['suffix'] if 'suffix' in data else None
        except Exception as e:
            logging.getLogger('maskgen').error("Failed to load plugin {}: {} ".format(name, str(e)))

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
    """
     :param reload:
     :param customFolders:
     :return:
     @rtype: PluginManager
    """
    if 'plugins' in config.global_config and not reload:
        return config.global_config['plugins']
    loaded = {}
    config.global_config['plugins'] = PluginManager(loaded)
    ps = getPlugins(customFolders=customFolders)
    for i in ps.keys():
        if 'custom' in ps[i]:
            path = ps[i]['custom']
            config.global_config['plugins'].loadCustom(i, path)
        else:
            _loadPluginModule(ps[i]['info'], i, loaded)
    return config.global_config['plugins']

def getOperations(fileType=None):
    return config.global_config['plugins'].getOperations(fileType=fileType)

def getPreferredSuffix(name,filetype= None):
    return config.global_config['plugins'].getPreferredSuffix(name,filetype=filetype)

def getOperation(name):
    parts = name.split('::')
    plugin_name = parts[0]
    op = config.global_config['plugins'].getOperation(plugin_name)
    if  op is not None and len(parts) > 1:
        op = copy.copy(op)
        op['name'] = op['name'] + '::' + parts[1]
    return op

def callPlugin(name,im,source,target,**kwargs):
    return config.global_config['plugins'].callPlugin(name.split('::')[0],im,source,target,**kwargs)

def _runCustomPlugin(command, im, source, target, **kwargs):
    import copy
    commands = copy.deepcopy(command['command'])
    mapping = copy.deepcopy(command['mapping'])
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
