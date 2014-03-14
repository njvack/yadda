#!/usr/bin/env python
# coding: utf8
"""
Watch source_dir for files, report them.

Usage:
  dicom_inotify.py [options] <source_dir>

Options:
  --timeout=<sec>  Timeout (in seconds) to wait for more files in a series
                   [default: 30]
  -h               Show this help screen.

"""
from __future__ import with_statement, division, print_function

import sys
import os
import logging
logger = logging.getLogger(__name__)

import yadda
from yadda import handlers, managers

from yadda.vendor.docopt import docopt
from yadda.vendor.schema import Schema, Use
from yadda.vendor import pyinotify
import dicom

SCHEMA = Schema({
    '<source_dir>': Use(os.path.expanduser),
    '--timeout': Use(float),
    str: object})


def main():
    arguments = docopt(__doc__, version=yadda.__version__)
    print(arguments)
    validated = SCHEMA.validate(arguments)
    print(validated)
    log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    logger.debug("Using log level {0}".format(log_level))
    return dicom_inotify(
        validated['<source_dir>'],
        validated['--timeout'])


def dicom_inotify(source_dir, timeout):
    wm = pyinotify.WatchManager()
    watch_mask = (
        pyinotify.IN_MOVED_TO |
        pyinotify.IN_CLOSE_WRITE |
        pyinotify.IN_CREATE)
    dicom_manager = MyDicomManager(timeout)
    fch = FileChangeHandler(dicom_manager=dicom_manager)
    notifier = pyinotify.ThreadedNotifier(wm, fch)
    wm.add_watch(source_dir, watch_mask, rec=True, auto_add=True)
    logger.info('Watching {0}'.format(source_dir))
    try:
        notifier.start()
        dicom_manager.wait()
    except KeyboardInterrupt:
        logger.debug("Keyboard Interrupt!")
        notifier.stop()
        dicom_manager.stop()


class FileChangeHandler(pyinotify.ProcessEvent):

    def my_init(self, dicom_manager):
        self.dicom_manager = dicom_manager

    def process_event(self, event):
        logger.debug('Processing {0}'.format(event.pathname))
        self.dicom_manager.handle_file(event.pathname)

    process_IN_MOVED_TO = process_event
    process_IN_CLOSE_WRITE = process_event
    process_IN_CREATE = process_event


class MyDicomManager(managers.ThreadedDicomManager):

    def handler_key(self, dcm):
        return str(dcm.SeriesNumber)

    def handle_file(self, filename):
        try:
            dcm = dicom.read_file(filename)
        except dicom.filereader.InvalidDicomError:
            logger.warn('Not a dicom: {0}'.format(filename))
            return
        self.handle_dicom(dcm, filename)

    def build_handler(self, dcm, filename):
        logger.debug(
            'Building a handler from {0}'.format(filename))
        return MyDicomHandler(self, self.handler_key(dcm), self.timeout)


class MyDicomHandler(handlers.ThreadedDicomHandler):
    def __init__(self, manager, name, timeout):
        super(MyDicomHandler, self).__init__(manager, name, timeout)

    def on_start(self):
        logger.debug('{0} on_start'.format(self))

    def on_handle(self, dcm, filename):
        logger.debug('{0} on_handle {1}'.format(self, filename))

    def on_finish(self):
        logger.debug('{0} on_finish'.format(self))

    def terminate(self):
        logger.debug('{0} terminate'.format(self))
        super(MyDicomHandler, self).terminate()


if __name__ == '__main__':
    sys.exit(main())
