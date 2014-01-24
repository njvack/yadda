#!/usr/bin/env python
# A simple, brutal test to make sure pydicom doesn't leak memory

import sys
import time
import dicom
import resource
import gc
import humanize

def run_test(duration, files):
    start = time.clock()

    while (time.clock() - start) < duration:
        print(humanize.naturalsize(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        for f in files:
            d = dicom.read_file(f)
        gc.collect()


if __name__ == '__main__':
    duration, files = sys.argv[1], sys.argv[2:]
    duration = float(duration)

    run_test(duration, files)