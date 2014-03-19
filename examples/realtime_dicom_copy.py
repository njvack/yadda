#!/usr/bin/env python
# coding: utf8
"""
Watch for dicoms, copy them to a temporary directory, then rename it when
the series is done. Organize directories by series, name them DATE-EXAM-SERIES

This script relies on pyinotify, and will hence run only on linux.

Usage:
  realtime_dicom_copy.py [options] <source_dir> <dest_dir>

Options:
  --timeout <sec>    Timeout (in seconds) to wait for more files in a series
                     [default: 30]
  --verbose, -v      Show lots of debugging.
  -h                 Show this help screen

"""
from __future__ import with_statement, division, print_function

import sys
import os
import shutil
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
    '<dest_dir>': Use(os.path.expanduser),
    '--timeout': Use(float),
    str: object})


def main():
    arguments = docopt(__doc__, version=yadda.__version__)
    print(arguments)
    validated = SCHEMA.validate(arguments)
    print(validated)
    log_level = logging.INFO
    if validated['--verbose']:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    return dicom_copier(
        source_dir=validated['<source_dir>'],
        dest_dir=validated['<dest_dir>'],
        timeout=validated['--timeout'])


def dicom_copier(source_dir, dest_dir, timeout):
    wm = pyinotify.WatchManager()
    watch_mask = (
        pyinotify.IN_MOVED_TO |
        pyinotify.IN_CLOSE_WRITE |
        pyinotify.IN_CREATE)
    dicom_manager = CopyingDicomManager(
        timeout=timeout,
        dest_dir=dest_dir)
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
        if event.dir:
            return
        logger.debug('Processing {0}'.format(event.pathname))
        try:
            self.dicom_manager.handle_file(event.pathname)
        except Exception as exc:
            logger.error('Error processing {0}: {1}'.format(
                event.pathname, exc))

    process_IN_MOVED_TO = process_event
    process_IN_CLOSE_WRITE = process_event
    process_IN_CREATE = process_event


class CopyingDicomManager(managers.ThreadedDicomManager):
    def __init__(self, timeout, dest_dir):
        super(CopyingDicomManager, self).__init__(timeout)
        self.dest_dir = dest_dir

    def handler_key(self, dcm):
        return '{0}-{1}-{2}'.format(
            dcm.StudyDate, dcm.StudyID, dcm.SeriesNumber)

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
        return CopyingDicomHandler(
            manager=self,
            name=self.handler_key(dcm),
            timeout=self.timeout,
            dest_dir=self.dest_dir)


class CopyingDicomHandler(handlers.ThreadedDicomHandler):
    def __init__(self, manager, name, timeout, dest_dir):
        self.dest_root = dest_dir
        self.temp_dir = os.path.join(dest_dir, '.'+name)
        self.final_dir = os.path.join(dest_dir, name)
        super(CopyingDicomHandler, self).__init__(manager, name, timeout)

    def on_start(self):
        logger.info('{0}: Creating directory {1}'.format(self, self.temp_dir))
        if os.path.isdir(self.temp_dir):
            logger.warn('{0}: {1} already exists'.format(self, self.temp_dir))
        else:
            os.makedirs(self.temp_dir)

    def on_handle(self, dcm, filename):
        logger.debug('{0}: Copy {1} -> {2}'.format(
            self, filename, self.temp_dir))
        shutil.copy(filename, self.temp_dir)

    def on_finish(self):
        logger.info('{0}: Move {1} -> {2}'.format(
            self, self.temp_dir, self.final_dir))
        os.rename(self.temp_dir, self.final_dir)

    def terminate(self):
        logger.warn('{0}: Forcing quit!'.format(self))
        super(CopyingDicomHandler, self).terminate()


if __name__ == '__main__':
    sys.exit(main())
