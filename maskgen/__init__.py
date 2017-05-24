import matplotlib
matplotlib.use("TkAgg")
from software_loader import loadOperations, loadSoftware, loadProjectProperties
import graph_rules
operations = 'operations.json'
software = 'software.csv'
projectProperties = 'project_properties.json'
loadOperations(operations)
loadSoftware(software)
loadProjectProperties(projectProperties)
graph_rules.setup()
