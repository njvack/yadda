#!/usr/bin/env python
# coding: utf8
"""
Watch source_dir for files; sort dicoms into dest_dir.

Usage:
  dicom_watch_sort.py [options] <source_dir> <dest_dir>

Options:
  --timeout=<sec>  Timeout (in seconds) to wait for more files in a series
                   [default: 30]
  -h               Show this help screen.
  -v, --verbose    Print what's going on.

"""
from __future__ import with_statement, division, print_function

import sys
import os
import logging
logger = logging.getLogger(__name__)

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer
import dicom

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
    """ Validate arguments and run dicom_watch_sort. """
    arguments = docopt(__doc__, version=yadda.__version__)
    print(arguments)
    validated = SCHEMA.validate(arguments)
    print(validated)
    log_level = logging.WARNING
    if arguments.get('--verbose'):
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    logging.info("Using log level {0}".format(log_level))
    return dicom_watch_sort(
        validated['<source_dir>'],
        validated['<dest_dir>'],
        validated['--timeout'])


def dicom_watch_sort(source_dir, dest_dir, timeout):
    """ Sort dicoms into subdirectories.

    Run through the source directory and copy all the dicoms, sorted into
    directory by series, into subdirectories of dest_dir.

    """
    logger.debug("Watching {0}".format(source_dir))
    manager = SortingDicomManager(timeout, dest_dir)
    handler = FileChangeHandler(manager)
    observer = Observer()
    observer.schedule(handler, source_dir, recursive=True)
    observer.start()
    try:
        manager.wait_for_files()
    except KeyboardInterrupt:
        logger.warn("Keyboard Interrupt!")
        observer.stop()
        manager.stop()


class FileChangeHandler(FileSystemEventHandler):

    def __init__(self, dicom_manager):
        super(FileChangeHandler, self).__init__()
        self.dicom_manager = dicom_manager
        self._event_map = {
            FileCreatedEvent: self.on_file_created
        }

    def on_any_event(self, event):
        callback = self._event_map.get(type(event))
        if callback:
            callback(event)

    def on_file_created(self, event):
        self.dicom_manager.handle_file(event.src_path)


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
        try:
            pass
            # os.makedirs(self.dest_dir)
        except OSError as err:
            logger.warn(str(err))

    def on_handle(self, dcm, filename):
        logger.info("{0}: {1} => {2}".format(
            self, filename, self.dest_dir))
        try:
            pass
            os.remove(filename)
            # shutil.move(filename, self.dest_dir)
        except OSError as e:
            logger.warn(e)

    def on_finish(self):
        logger.info("{0}: finishing!".format(self))

    def __str__(self):
        return self.name

    def terminate(self):
        logger.warn("{0}: Terminating!".format(self))
        super(SortingDicomHandler, self).terminate()


if __name__ == '__main__':
    sys.exit(main())
