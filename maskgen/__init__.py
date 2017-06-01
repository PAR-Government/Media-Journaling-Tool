import matplotlib
matplotlib.use("TkAgg")
import logging
from loghandling import set_logging
set_logging()
import software_loader
from image_graph import igversion
logging.getLogger('maskgen').info('Version ' + igversion)
import graph_rules
graph_rules.setup()

