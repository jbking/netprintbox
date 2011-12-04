import os


def normalize_name(path):
    return os.path.basename(path).split(os.path.extsep)[0]

