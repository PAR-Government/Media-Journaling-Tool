import scenario_model
import tool_set
import numpy as np

def opacityAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(),directory='.'):
    scModel = arguments['sc_model']
    start = arguments['start_node']
    end = arguments['end_node']
    donor_node_list = [ n for n in scModel.G.predecessors(end)  if n != start]
    if len(donor_node_list) == 0:
        return
    donor_node = donor_node_list[0]
    donorImage = scModel.G.get_image(donor_node)[0]
    donorMask = scModel.G.get_edge_image(donor_node, end, 'maskname')
    edge = scModel.G.get_edge(donor_node,end)
    tm = tool_set.deserializeMatrix(edge['transform matrix']) if 'transform matrix' in edge else None
    result = tool_set.generateOpacityImage(img1.to_array(), donorImage.to_array(), img2.to_array(), 255-mask.to_array(), donorMask.to_array(),tm)
    analysis['opacity_estimate'] = np.mean(result)