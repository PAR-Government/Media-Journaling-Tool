import matplotlib
matplotlib.use("TkAgg")
import logging
from loghandling import set_logging
set_logging()
from image_graph import igversion
logging.getLogger('maskgen').info('Version ' + igversion)
import software_loader
import graph_rules
graph_rules.setup()

