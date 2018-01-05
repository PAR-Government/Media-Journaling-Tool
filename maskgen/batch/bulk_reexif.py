import argparse

from maskgen import scenario_model
from maskgen.batch import BatchProcessor
from maskgen.software_loader import *
from maskgen import graph_rules, plugins
import os
from maskgen.batch import pick_projects
from maskgen.tool_set import getValue

def rerunexif( project):
    """
    Save error report, project properties, composites, and donors
    :param sm: scenario model
    """
    sm = scenario_model.ImageProjectModel(project)
    plugin_map = {
        'AntiForensicExifQuantizationTable': 'CompressAs',
        'AntiForensicCopyExif': 'ExifMetaCopy',
        'AntiForensicEditExif': 'ExifGPSCopy'
    }
    for edge_id in sm.getGraph().get_edges():
        edge = sm.getGraph().get_edge(edge_id[0], edge_id[1])
        # if a compression type operation
        if edge['op'] in ['AntiForensicExifQuantizationTable', 'AntiForensicCopyExif', 'AntiForensicEditExif']:
            # has donor
            preds = [pred for pred in sm.getGraph().predecessors(edge_id[1]) if pred != edge_id[0]]
            if len(preds) > 0:
                donor_node = sm.getGraph().get_node(preds[0])
                target_node = sm.getGraph().get_node(edge_id[1])
                im, source_filename = sm.getImageAndName(edge_id[0])
                target_filenanme = os.path.join(sm.get_dir(), target_node['file'])
                plugin_name = plugin_map[edge['op']]
                kwargs = {'donor':os.path.join(sm.get_dir(), donor_node['file']),
                         'rotate':'yes'}
                doc = getValue(edge,'arguments.degrees of change')
                if doc is not None:
                    kwargs['degrees of change'] = doc
                plugins.callPlugin(plugin_name,
                                   im,
                                   source_filename,
                                   target_filenanme,
                                   **kwargs)
            sm.reproduceMask(edge_id=edge_id)
    sm.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', help='Directory of projects')
    parser.add_argument('-cf', '--completefile', required=True, help='Projects to Completed')
    parser.add_argument('-t', '--threads', required=False, default=1, help='Threads')
    args = parser.parse_args()

    project_list = pick_projects(args.projects)
    processor = BatchProcessor(args.completefile, project_list,threads=int(args.threads))
    processor.process(rerunexif)



if __name__ == '__main__':
    main()
