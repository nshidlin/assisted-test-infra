import os
import pkg_resources


def main():
    makefile = pkg_resources.resource_filename('assisted_test_infra', 'data/Makefile')

    os.system(f'make -f {makefile} image_build')
    cwd = os.getcwd()
    os.environ("TEST") = cwd
    os.system(f'make -f {makefile} test')

