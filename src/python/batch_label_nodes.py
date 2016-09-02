import argparse
import os
import scenario_model
import bulk_export

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    args = parser.parse_args()

    dirs = bulk_export.pick_dirs(args.dir)
    total = len(dirs)
    count = 1
    for d in dirs:
        sm = scenario_model.ImageProjectModel(d)
        p = sm.getNodeNames()
        for node in p:
            sm.labelNodes(node)
        sm.save()
        print 'Project updated [' + str(count) + '/' + str(total) + '] '+ os.path.basename(d)
        count+=1

if __name__ == '__main__':
    main()
