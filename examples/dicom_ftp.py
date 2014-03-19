#!/usr/bin/env python
# coding: utf8
"""
Watch for dicoms, FTP them to a specific place on a server. Files are
organized into directories by series, in the format:
DATE-EXAM-SERIES

This script relies on pyinotify, and will hence run only on linux.

Usage:
  dicom_ftp.py [options] <source_dir> <host> [<port>]

Options:
  --dest-dir <dir>   Base directory on host to put files
  --user <user>      FTP username [default: anonymous]
  --password <pw>    FTP password
  --timeout <sec>    Timeout (in seconds) to wait for more files in a series
                     [default: 30]
  --verbose, -v      Show lots of debugging.
  -h                 Show this help screen

"""
from __future__ import with_statement, division, print_function

import sys
import os
import logging
logger = logging.getLogger(__name__)

from ftplib import FTP

import yadda
from yadda import handlers, managers

from yadda.vendor.docopt import docopt
from yadda.vendor.schema import Schema, Use, SchemaError
from yadda.vendor import pyinotify
import dicom


class UseDefault(object):
    def __init__(self, _callable, _default):
        self._callable = _callable
        self._default = _default

    def validate(self, data):
        if data is None:
            return self._default
        try:
            return self._callable(data)
        except Exception as e:
            raise SchemaError('%r raised %r' % (self._callable.__name__, e))


SCHEMA = Schema({
    '<source_dir>': Use(os.path.expanduser),
    '<port>': UseDefault(int, 21),
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
    return dicom_ftp(
        source_dir=validated['<source_dir>'],
        timeout=validated['--timeout'],
        host=validated['<host>'],
        port=validated['<port>'],
        ftp_user=validated['--user'],
        ftp_pw=validated['--password'],
        initial_dir=validated.get('--dest-dir'))


def dicom_ftp(
        source_dir, timeout, host, port, ftp_user, ftp_pw, initial_dir):
    wm = pyinotify.WatchManager()
    watch_mask = (
        pyinotify.IN_MOVED_TO |
        pyinotify.IN_CLOSE_WRITE |
        pyinotify.IN_CREATE)
    dicom_manager = FTPDicomManager(
        timeout=timeout,
        host=host,
        port=port,
        ftp_user=ftp_user,
        ftp_pw=ftp_pw,
        initial_dir=initial_dir)
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
        self.dicom_manager.handle_file(event.pathname)
        # except Exception as exc:
        #     logger.error('Error processing {0}: {1}'.format(
        #         event.pathname, exc))

    process_IN_MOVED_TO = process_event
    process_IN_CLOSE_WRITE = process_event
    process_IN_CREATE = process_event


class FTPDicomManager(managers.ThreadedDicomManager):
    def __init__(self, timeout, host, port, ftp_user, ftp_pw, initial_dir):
        super(FTPDicomManager, self).__init__(timeout)
        self.host = host
        self.port = port
        self.ftp_user = ftp_user
        self.ftp_pw = ftp_pw
        self.initial_dir = initial_dir

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
        return FTPDicomHandler(
            manager=self,
            name=self.handler_key(dcm),
            timeout=self.timeout,
            host=self.host,
            port=self.port,
            ftp_user=self.ftp_user,
            ftp_pw=self.ftp_pw,
            initial_dir=self.initial_dir)


class FTPDicomHandler(handlers.ThreadedDicomHandler):
    def __init__(
            self, manager, name, timeout,
            host, port, ftp_user, ftp_pw, initial_dir):
        self.host = host
        self.port = port
        self.ftp_user = ftp_user
        self.ftp_pw = ftp_pw
        self.initial_dir = initial_dir
        self.ftp = FTP()
        super(FTPDicomHandler, self).__init__(manager, name, timeout)

    def on_start(self):
        logger.debug('{0}: Connecting to {1}:{2}'.format(
            self, self.host, self.port))
        self.ftp.connect(self.host, self.port)
        logger.debug('{0}: Connected.')
        logger.debug('{0}: Logging in as {1}:{2}'.format(
            self, self.ftp_user, self.ftp_pw))
        self.ftp.login(self.ftp_user, self.ftp_pw)
        logger.debug('{0}: Logged in.')
        if self.initial_dir is not None:
            logger.debug('{0}: cwd to {1}'.format(self, self.initial_dir))
            self.ftp.cwd(self.initial_dir)
        dir_name = '.'+str(self)
        logger.debug('{0}: Creating directory {1}'.format(self, dir_name))
        self.ftp.mkd(dir_name)
        self.ftp.cwd(dir_name)
        logger.info('{0}: Ready to upload')

    def on_handle(self, dcm, filename):
        base_filename = os.path.basename(filename)
        logger.debug('{0}: Uploading {1}'.format(self, filename))
        cmd = 'STOR ' + base_filename
        with open(filename, 'r') as f:
            self.ftp.storbinary(cmd, f)

    def on_finish(self):
        logger.info('{0}: Renaming directory'.format(self))
        self.ftp.cwd('..')
        self.ftp.rename('.'+str(self), str(self))
        self.ftp.quit()

    def terminate(self):
        logger.warn('{0}: Forcing quit!'.format(self))
        super(FTPDicomHandler, self).terminate()


if __name__ == '__main__':
    sys.exit(main())
