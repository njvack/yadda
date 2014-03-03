#!/usr/bin/env python
# coding: utf8
"""
Example: Crawl a directory and sort the dicoms in it to a destination.

Usage:
  dicom_walk_sort [options] <source_dir> <dest_dir>

Options:
  --timeout=<sec>  Timeout (in seconds) to wait for more files
                   [default: 30]
  -h               Show this help screen.
  -v, --verbose    Print what's going on.

"""
from __future__ import with_statement, division, print_function

import sys
import os
import shutil
import dicom
import logging
from time import time
logger = logging.getLogger(__name__)

from yadda.vendor.docopt import docopt
from yadda.vendor.schema import Schema, Use

import yadda
from yadda import handlers, managers

SCHEMA = Schema({
    '<source_dir>': Use(os.path.expanduser),
    '<dest_dir>': Use(os.path.expanduser),
    '--timeout': Use(float),
    str: object})


def main():
    """ Validate arguments and run dicom_sort_walk. """
    arguments = docopt(__doc__, version=yadda.__version__)
    print(arguments)
    validated = SCHEMA.validate(arguments)
    print(validated)
    log_level = logging.WARNING
    if arguments.get('--verbose'):
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    logging.info("Using log level {0}".format(log_level))
    return dicom_sort_walk(
        validated['<source_dir>'],
        validated['<dest_dir>'],
        validated['--timeout'])


def dicom_sort_walk(source_dir, dest_dir, timeout):
    """ Sort dicoms into subdirectories.

    Run through the source directory and copy all the dicoms, sorted into
    directory by series, into subdirectories of dest_dir.

    """
    mgr = SortingDicomManager(timeout, dest_dir)
    logger.debug("Watching {0}".format(source_dir))
    start_time = time()
    file_count = 0
    for info in os.walk(source_dir):
        files = info[2]
        file_count += len(files)
        for f in files:
            full_file = os.path.join(source_dir, info[0], f)
            mgr.handle_file(full_file)
    elapsed = time() - start_time
    logger.info("{0} files, {1} seconds, {2} files/sec".format(
        file_count, elapsed, file_count/elapsed))


class SortingDicomManager(managers.ThreadedDicomManager):
    def __init__(self, timeout, destination_base):
        self.destination_base = destination_base
        super(SortingDicomManager, self).__init__(timeout)

    def handler_key(self, dicom):
        return str(dicom.SeriesNumber)

    def handle_file(self, filename):
        try:
            dcm = dicom.read_file(filename)
        except dicom.filereader.InvalidDicomError:
            return
        self.handle_dicom(dcm, filename)

    def handle_dicom(self, dcm, filename):
        logger.debug((dcm.SeriesNumber, filename))
        super(SortingDicomManager, self).handle_dicom(dcm, filename)

    def build_handler(self, sample_dicom, filename):
        series_number = str(sample_dicom.SeriesNumber)
        dest_dir = os.path.join(self.destination_base, series_number)
        return SortingDicomHandler(
            self, series_number, self.timeout, dest_dir)


class SortingDicomHandler(handlers.ThreadedDicomHandler):
    def __init__(self, manager, name, timeout, dest_dir):
        super(SortingDicomHandler, self).__init__(manager, name, timeout)
        self.dest_dir = dest_dir

    def on_start(self):
        logger.info("{0}: creating {1}".format(self, self.dest_dir))
        os.makedirs(self.dest_dir)

    def on_handle(self, dcm, filename):
        shutil.copy(filename, self.dest_dir)
        logger.info("{0}: handling {1}".format(self, filename))

    def on_finish(self):
        logger.warn(self.manager)
        logger.info("{0}: finishing!".format(self))

    def __str__(self):
        return self.name


if __name__ == '__main__':
    sys.exit(main())
