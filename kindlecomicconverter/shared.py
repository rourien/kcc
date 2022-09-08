# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2014 Ciro Mattia Gonano <ciromattia@gmail.com>
# Copyright (c) 2013-2019 Pawel Jastrzebski <pawelj@iosphe.re>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all
# copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
# AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
# DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA
# OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

import os
from hashlib import md5
from html.parser import HTMLParser
from distutils.version import StrictVersion
from re import split
from traceback import format_tb
from stat import S_IWRITE, S_IREAD, S_IEXEC
from shutil import rmtree, copytree
from psutil import disk_usage
from tempfile import mkdtemp, gettempdir
from . import comicarchive
from . import pdfjpgextract


class HTMLStripper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

    def error(self, message):
        pass


def getImageFileName(imgfile):
    name, ext = os.path.splitext(imgfile)
    ext = ext.lower()
    if (name.startswith('.') and len(name) == 1) or ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        return None
    return [name, ext]


def getDirectorySize(start_path='.'):
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def getWorkFolder(afile, name, ebook=True):
    if os.path.isdir(afile):
        if disk_usage(gettempdir())[2] < getDirectorySize(afile) * 2.5:
            raise UserWarning("Not enough disk space to perform conversion.")
        workdir = mkdtemp('', name)
        try:
            os.rmdir(workdir)
            if ebook:
                fullPath = os.path.join(workdir, 'OEBPS', 'Images')
            else:
                fullPath = workdir
            copytree(afile, fullPath)
            sanitizePermissions(fullPath)
            return os.path.abspath(workdir)
        except Exception:
            rmtree(workdir, True)
            raise UserWarning("Failed to prepare a workspace.")
    elif os.path.isfile(afile):
        if disk_usage(gettempdir())[2] < os.path.getsize(afile) * 2.5:
            raise UserWarning("Not enough disk space to perform conversion.")
        if str(afile).lower().endswith('.pdf'):
            pdf = pdfjpgextract.PdfJpgExtract(afile)
            path, njpg = pdf.extract()
            if njpg == 0:
                rmtree(path, True)
                raise UserWarning("Failed to extract images from PDF file.")
        else:
            workdir = mkdtemp('', name)
            try:
                cbx = comicarchive.ComicArchive(afile)
                path = cbx.extract(workdir)
            except OSError as e:
                rmtree(workdir, True)
                raise UserWarning(e.strerror)
        sanitizePermissions(path)
        newpath = mkdtemp('', name)
        if ebook:
            copytree(path, os.path.join(newpath, 'OEBPS', 'Images'))
        else:
            copytree(path, workdir)
        rmtree(path, True)
        return os.path.abspath(newpath)
    else:
        raise UserWarning("Failed to open source file/directory.")


def walkSort(dirnames, filenames):
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in split('([0-9]+)', key)]
    dirnames.sort(key=lambda name: alphanum_key(name.lower()))
    filenames.sort(key=lambda name: alphanum_key(name.lower()))
    return dirnames, filenames


def walkLevel(some_dir, level=1):
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        dirs, files = walkSort(dirs, files)
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]


def md5Checksum(fpath):
    with open(fpath, 'rb') as fh:
        m = md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()


def sanitizeTrace(traceback):
    return ''.join(format_tb(traceback))\
        .replace('C:/projects/kcc/', '')\
        .replace('c:/projects/kcc/', '')\
        .replace('C:/python37-x64/', '')\
        .replace('c:/python37-x64/', '')\
        .replace('C:\\projects\\kcc\\', '')\
        .replace('c:\\projects\\kcc\\', '')\
        .replace('C:\\python37-x64\\', '')\
        .replace('c:\\python37-x64\\', '')


def sanitizePermissions(filetree):
    for root, dirs, files in os.walk(filetree, False):
        for name in files:
            os.chmod(os.path.join(root, name), S_IWRITE | S_IREAD)
        for name in dirs:
            os.chmod(os.path.join(root, name), S_IWRITE | S_IREAD | S_IEXEC)


# noinspection PyUnresolvedReferences
def dependencyCheck(level):
    missing = []
    if level > 2:
        try:
            from PyQt5.QtCore import qVersion as qtVersion
            if StrictVersion('5.6.0') > StrictVersion(qtVersion()):
                missing.append('PyQt 5.6.0+')
        except ImportError:
            missing.append('PyQt 5.6.0+')
        try:
            import raven
        except ImportError:
            missing.append('raven 6.0.0+')
    if level > 1:
        try:
            from psutil import __version__ as psutilVersion
            if StrictVersion('5.0.0') > StrictVersion(psutilVersion):
                missing.append('psutil 5.0.0+')
        except ImportError:
            missing.append('psutil 5.0.0+')
        try:
            from slugify import __version__ as slugifyVersion
            if StrictVersion('1.2.1') > StrictVersion(slugifyVersion):
                missing.append('python-slugify 1.2.1+')
        except ImportError:
            missing.append('python-slugify 1.2.1+')
    try:
        from PIL import __version__ as pillowVersion
        if StrictVersion('5.2.0') > StrictVersion(pillowVersion):
            missing.append('Pillow 5.2.0+')
    except ImportError:
        missing.append('Pillow 5.2.0+')
    if len(missing) > 0:
        print('ERROR: ' + ', '.join(missing) + ' is not installed!')
        exit(1)
