import re


class SeedProcessor:
    def __init__(self, master, seed_file):
        self.master = master
        self.seed_file = seed_file
        self.seeds = {}
        self.read_seeds()

    def read_seeds(self):
        with open(self.seed_file) as f:
            lines = f.read().split("Image")[1:]

        i = 0
        for line in lines:
            s = line.split(" : ")[1]

            no_n = re.compile(r'[\n]').sub('', s)

            # To avoid starting with '[, '
            if no_n.startswith('[ '):
                no_n = no_n[2:]
                pos = True
            else:
                pos = False

            no_s = re.compile(r'[\s]+').sub(', ', no_n)
            self.seeds[i] = '[ ' + no_s if pos else no_s
            i += 1

    def get_seeds(self):
        return self.seeds.values()

    def get_seed_by_image(self, number):
        return self.seeds[number]
