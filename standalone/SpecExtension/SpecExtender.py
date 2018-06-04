import json
import os
import copy
import argparse

def critlinks(l,i):
    imp = []
    for link in l:
        s = link['source']
        t = link['target']
        if s in i or t in i:
            imp.append(copy.copy(link))
    return imp

def linkdelete(l,i):
    lt = copy.deepcopy(l)
    for link in lt:
        s = link['source']
        t = link['target']
        if s in i or t in i:
            l.pop(l.index(link))

def replace(l,p,n):
    for i in range(len(l)):
        s = l[i]['source']
        t = l[i]['target']
        if s == p:
            l[i]['source'] = n
        if t == p:
            l[i]['target'] = n
    return l


def getNodeIds(jsf):
   nodes = jsf['nodes']
   return [ node['id'] for node in nodes if node['id'].endswith('#')]

def extend(jsf, fi , subgraph, dir=None, count = 1):
    files = os.listdir(dir) if dir is not None else []
    nodes = list(jsf['nodes'])
    links = list(jsf['links'])
    indexes = [n['id'] for n in nodes]
    for m in range(count):
        li = critlinks(links,list((subgraph)))
        for g in subgraph:
            ind = indexes.index(g)
            n = copy.deepcopy(jsf['nodes'][ind])
            if 'files' in n and n['files'][0][0] == '*':
                if len(files) == 0:
                    break
                n['files'][0] = os.path.join(dir,files.pop(0))
            if 'arguments' in n and 'donor' in n['arguments'] and n['arguments']['donor']['source'][-1] == '#':
                n['arguments']['donor']['source'] += str(m)
            n['id'] = str(n['id']+str(m))
            li = replace(li,g,n['id'])
            jsf['nodes'].append(n)
        jsf['links'].extend(li)
    for g in subgraph:
        ind = indexes.index(g)
        jsf['nodes'].pop(ind)
        indexes = [n['id'] for n in jsf['nodes']]
    linkdelete(jsf['links'],subgraph)

    wf = open(os.path.join(os.path.split(fi)[0],'dup.json'),'w+')
    json.dump(jsf,wf, indent = 4, ensure_ascii = False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', required=True, help='JSON File')
    parser.add_argument('--count', required=False, default=1, help='The amount of duplicates')
    args = parser.parse_args()
    fi = args.json
    jsf = json.load(open(fi))
    subgraph = getNodeIds(jsf)
    extend(jsf,fi,subgraph,count=int(args.count))

if __name__ == '__main__':
    main()
