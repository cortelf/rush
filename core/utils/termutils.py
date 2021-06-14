from platform import system
from subprocess import check_output


def get_max_descriptors():
    try:
        return int(check_output('ulimit -n', shell=True))
    except ValueError:
        # failed by some reason
        return None


def is_linux():
    return system() == 'Linux'