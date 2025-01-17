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
import sys
import argparse
from time import strftime, gmtime
from copy import copy
from glob import glob, escape
from re import compile, sub
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from tempfile import mkdtemp, gettempdir, TemporaryFile
from shutil import move, rmtree, copyfile
from multiprocessing import Pool
from uuid import uuid4
from slugify import slugify as slugifyExt
from PIL import Image, ImageColor
from subprocess import STDOUT, PIPE
from psutil import Popen, virtual_memory
from html import escape as hescape
try:
    from PyQt5 import QtCore
except ImportError:
    QtCore = None
from .shared import md5Checksum, getImageFileName, walkSort, walkLevel, sanitizeTrace, \
                    getDirectorySize, getWorkFolder
from . import comic2panel
from . import image
from . import dualmetafix
from . import metadata
from . import kindle
from . import __version__


def main(argv=None):
    global options, alreadyexistslist, alreadyprocessedlist, copyprocessedlist, multiprocessedlist, completedlist
    alreadyexistslist = []
    alreadyprocessedlist = []
    copyprocessedlist = []
    multiprocessedlist = []
    completedlist = []
    sourcefiles = []
    countsourcefiles = 1
    ext = (".cbz",".zip",".cbr",".rar",".cb7",".7z",".pdf")
    parser = makeParser()
    args = parser.parse_args(argv)
    options = copy(args)
    if options.help:
        optionsHelp()
        return 0
    if not argv or options.input == []:
        parser.print_help()
        return 0
    if sys.platform.startswith('win'):
        sources = set([source for option in options.input for source in glob(escape(option))])
    else:
        sources = set(options.input)
    if len(sources) == 0:
        print('No matching files found.')
        return 1
    for source in sources:
        source = source.rstrip('\\').rstrip('/')
        options = copy(args)
        checkOptions()
        if options.batchsplit == 0:
            if os.path.isdir(source):
                for dirpath, _, filenames in os.walk(source):
                    for filename in filenames:
                        if str(filename).endswith(ext):
                            sourcefiles.append(os.path.join(dirpath,filename))
            elif str(source).endswith(ext):
                sourcefiles.append(source)
        else:
            print("\nWorking on " + os.path.normpath(source))
            makeBook(source)
    for sourcefile in sourcefiles:
        print("\nWorking on " + "(" + str(countsourcefiles) + "/" + str(len(sourcefiles)) + ") - " +
                os.path.normpath(sourcefile))
        makeBook(sourcefile)
        countsourcefiles += 1
    if alreadyexistslist:
        print("\nThe following file(s) already exist in the output directory and were skipped:")
        for alreadyexists in alreadyexistslist:
            print(os.path.normpath(alreadyexists))
    if alreadyprocessedlist:
        print("\nThe following file(s) were probably created by KCC and were skipped:")
        for alreadprocessed in alreadyprocessedlist:
            print(os.path.normpath(alreadprocessed))
    if copyprocessedlist:
        print("\nThe following file(s) were probably created by KCC and copied to the output directory:")
        for copyprocessed in copyprocessedlist:
            print(os.path.normpath(copyprocessed))
    if multiprocessedlist:
        print("\nWARNING: The following file(s) were probably created by KCC. The second conversion decreased"
              " quality:")
        for multiprocessed in multiprocessedlist:
            print(os.path.normpath(multiprocessed))
    if completedlist:
        print("\nThe following file(s) were successfully generated:")
        for completed in completedlist:
            print(os.path.normpath(completed))
    return 0


def buildHTML(path, imgfile, imgfilepath):
    imgfilepath = md5Checksum(imgfilepath)
    filename = getImageFileName(imgfile)
    deviceres = options.profileData[1]
    if "Rotated" in options.imgMetadata[imgfilepath]:
        rotatedPage = True
    else:
        rotatedPage = False
    if "BlackBackground" in options.imgMetadata[imgfilepath]:
        additionalStyle = 'background-color:#000000;'
    else:
        additionalStyle = ''
    postfix = ''
    backref = 1
    head = path
    while True:
        head, tail = os.path.split(head)
        if tail == 'Images':
            htmlpath = os.path.join(head, 'Text', postfix)
            break
        postfix = tail + "/" + postfix
        backref += 1
    if not os.path.exists(htmlpath):
        os.makedirs(htmlpath)
    htmlfile = os.path.join(htmlpath, filename[0] + '.xhtml')
    imgsize = Image.open(os.path.join(head, "Images", postfix, imgfile)).size
    if options.hq:
        imgsizeframe = (int(imgsize[0] // 1.5), int(imgsize[1] // 1.5))
    else:
        imgsizeframe = imgsize
    f = open(htmlfile, "w", encoding='UTF-8')
    f.writelines(["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
                  "<!DOCTYPE html>\n",
                  "<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\">\n",
                  "<head>\n",
                  "<title>", hescape(filename[0]), "</title>\n",
                  "<link href=\"", "../" * (backref - 1), "style.css\" type=\"text/css\" rel=\"stylesheet\"/>\n",
                  "<meta name=\"viewport\" "
                  "content=\"width=" + str(imgsize[0]) + ", height=" + str(imgsize[1]) + "\"/>\n"
                  "</head>\n",
                  "<body style=\"" + additionalStyle + "\">\n",
                  "<div style=\"text-align:center;top:" + getTopMargin(deviceres, imgsizeframe) + "%;\">\n",
                  "<img width=\"" + str(imgsizeframe[0]) + "\" height=\"" + str(imgsizeframe[1]) + "\" ",
                  "src=\"", "../" * backref, "Images/", postfix, imgfile, "\"/>\n</div>\n"])
    if options.iskindle and options.panelview:
        if options.autoscale:
            size = (getPanelViewResolution(imgsize, deviceres))
        else:
            if options.hq:
                size = imgsize
            else:
                size = (int(imgsize[0] * 1.5), int(imgsize[1] * 1.5))
        if size[0] - deviceres[0] < deviceres[0] * 0.01:
            noHorizontalPV = True
        else:
            noHorizontalPV = False
        if size[1] - deviceres[1] < deviceres[1] * 0.01:
            noVerticalPV = True
        else:
            noVerticalPV = False
        x, y = getPanelViewSize(deviceres, size)
        boxStyles = {"PV-TL": "position:absolute;left:0;top:0;",
                     "PV-TR": "position:absolute;right:0;top:0;",
                     "PV-BL": "position:absolute;left:0;bottom:0;",
                     "PV-BR": "position:absolute;right:0;bottom:0;",
                     "PV-T": "position:absolute;top:0;left:" + x + "%;",
                     "PV-B": "position:absolute;bottom:0;left:" + x + "%;",
                     "PV-L": "position:absolute;left:0;top:" + y + "%;",
                     "PV-R": "position:absolute;right:0;top:" + y + "%;"}
        f.write("<div id=\"PV\">\n")
        if not noHorizontalPV and not noVerticalPV:
            if rotatedPage:
                if options.righttoleft:
                    order = [1, 3, 2, 4]
                else:
                    order = [2, 4, 1, 3]
            else:
                if options.righttoleft:
                    order = [2, 1, 4, 3]
                else:
                    order = [1, 2, 3, 4]
            boxes = ["PV-TL", "PV-TR", "PV-BL", "PV-BR"]
        elif noHorizontalPV and not noVerticalPV:
            if rotatedPage:
                if options.righttoleft:
                    order = [1, 2]
                else:
                    order = [2, 1]
            else:
                order = [1, 2]
            boxes = ["PV-T", "PV-B"]
        elif not noHorizontalPV and noVerticalPV:
            if rotatedPage:
                order = [1, 2]
            else:
                if options.righttoleft:
                    order = [2, 1]
                else:
                    order = [1, 2]
            boxes = ["PV-L", "PV-R"]
        else:
            order = []
            boxes = []
        for i in range(0, len(boxes)):
            f.writelines(["<div id=\"" + boxes[i] + "\">\n",
                          "<a style=\"display:inline-block;width:100%;height:100%;\" class=\"app-amzn-magnify\" "
                          "data-app-amzn-magnify='{\"targetId\":\"" + boxes[i] +
                          "-P\", \"ordinal\":" + str(order[i]) + "}'></a>\n",
                          "</div>\n"])
        f.write("</div>\n")
        for box in boxes:
            f.writelines(["<div class=\"PV-P\" id=\"" + box + "-P\" style=\"" + additionalStyle + "\">\n",
                          "<img style=\"" + boxStyles[box] + "\" src=\"", "../" * backref, "Images/", postfix,
                          imgfile, "\" width=\"" + str(size[0]) + "\" height=\"" + str(size[1]) + "\"/>\n",
                          "</div>\n"])
    f.writelines(["</body>\n",
                  "</html>\n"])
    f.close()
    return path, imgfile


def buildNCX(dstdir, title, chapters, chapternames):
    ncxfile = os.path.join(dstdir, 'OEBPS', 'toc.ncx')
    f = open(ncxfile, "w", encoding='UTF-8')
    f.writelines(["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
                  "<ncx version=\"2005-1\" xml:lang=\"en-US\" xmlns=\"http://www.daisy.org/z3986/2005/ncx/\">\n",
                  "<head>\n",
                  "<meta name=\"dtb:uid\" content=\"urn:uuid:", options.uuid, "\"/>\n",
                  "<meta name=\"dtb:depth\" content=\"1\"/>\n",
                  "<meta name=\"dtb:totalPageCount\" content=\"0\"/>\n",
                  "<meta name=\"dtb:maxPageNumber\" content=\"0\"/>\n",
                  "<meta name=\"generated\" content=\"true\"/>\n",
                  "</head>\n",
                  "<docTitle><text>", hescape(title), "</text></docTitle>\n",
                  "<navMap>\n"])
    for chapter in chapters:
        folder = chapter[0].replace(os.path.join(dstdir, 'OEBPS'), '').lstrip('/').lstrip('\\\\')
        filename = getImageFileName(os.path.join(folder, chapter[1]))
        navID = folder.replace('/', '_').replace('\\', '_')
        if options.chapters:
            title = chapternames[chapter[1]]
            navID = filename[0].replace('/', '_').replace('\\', '_')
        elif os.path.basename(folder) != "Text":
            title = chapternames[os.path.basename(folder)]
        f.write("<navPoint id=\"" + navID + "\"><navLabel><text>" +
                hescape(title) + "</text></navLabel><content src=\"" + filename[0].replace("\\", "/") +
                ".xhtml\"/></navPoint>\n")
    f.write("</navMap>\n</ncx>")
    f.close()


def buildNAV(dstdir, title, chapters, chapternames):
    navfile = os.path.join(dstdir, 'OEBPS', 'nav.xhtml')
    f = open(navfile, "w", encoding='UTF-8')
    f.writelines(["<?xml version=\"1.0\" encoding=\"utf-8\"?>\n",
                  "<!DOCTYPE html>\n",
                  "<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\">\n",
                  "<head>\n",
                  "<title>" + hescape(title) + "</title>\n",
                  "<meta charset=\"utf-8\"/>\n",
                  "</head>\n",
                  "<body>\n",
                  "<nav xmlns:epub=\"http://www.idpf.org/2007/ops\" epub:type=\"toc\" id=\"toc\">\n",
                  "<ol>\n"])
    for chapter in chapters:
        folder = chapter[0].replace(os.path.join(dstdir, 'OEBPS'), '').lstrip('/').lstrip('\\\\')
        filename = getImageFileName(os.path.join(folder, chapter[1]))
        if options.chapters:
            title = chapternames[chapter[1]]
        elif os.path.basename(folder) != "Text":
            title = chapternames[os.path.basename(folder)]
        f.write("<li><a href=\"" + filename[0].replace("\\", "/") + ".xhtml\">" + hescape(title) + "</a></li>\n")
    f.writelines(["</ol>\n",
                  "</nav>\n",
                  "<nav epub:type=\"page-list\">\n",
                  "<ol>\n"])
    for chapter in chapters:
        folder = chapter[0].replace(os.path.join(dstdir, 'OEBPS'), '').lstrip('/').lstrip('\\\\')
        filename = getImageFileName(os.path.join(folder, chapter[1]))
        if options.chapters:
            title = chapternames[chapter[1]]
        elif os.path.basename(folder) != "Text":
            title = chapternames[os.path.basename(folder)]
        f.write("<li><a href=\"" + filename[0].replace("\\", "/") + ".xhtml\">" + hescape(title) + "</a></li>\n")
    f.write("</ol>\n</nav>\n</body>\n</html>")
    f.close()


def buildOPF(dstdir, title, filelist, cover=None):
    opffile = os.path.join(dstdir, 'OEBPS', 'content.opf')
    deviceres = options.profileData[1]
    if options.righttoleft:
        writingmode = "horizontal-rl"
    else:
        writingmode = "horizontal-lr"
    f = open(opffile, "w", encoding='UTF-8')
    f.writelines(["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
                  "<package version=\"3.0\" unique-identifier=\"BookID\" ",
                  "xmlns=\"http://www.idpf.org/2007/opf\">\n",
                  "<metadata xmlns:opf=\"http://www.idpf.org/2007/opf\" ",
                  "xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\n",
                  "<dc:title>", hescape(title), "</dc:title>\n",
                  "<dc:language>en-US</dc:language>\n",
                  "<dc:identifier id=\"BookID\">urn:uuid:", options.uuid, "</dc:identifier>\n",
                  "<dc:contributor id=\"contributor\">KindleComicConverter-" + __version__ + "</dc:contributor>\n"])
    if len(options.summary) > 0:
        f.writelines(["<dc:description>", options.summary, "</dc:description>\n"])
    for author in options.authors:
        f.writelines(["<dc:creator>", author, "</dc:creator>\n"])
    f.writelines(["<meta property=\"dcterms:modified\">" + strftime("%Y-%m-%dT%H:%M:%SZ", gmtime()) + "</meta>\n",
                  "<meta name=\"cover\" content=\"cover\"/>\n"])
    if options.iskindle and options.profile != 'Custom':
        f.writelines(["<meta name=\"fixed-layout\" content=\"true\"/>\n",
                      "<meta name=\"original-resolution\" content=\"",
                      str(deviceres[0]) + "x" + str(deviceres[1]) + "\"/>\n",
                      "<meta name=\"book-type\" content=\"comic\"/>\n",
                      "<meta name=\"primary-writing-mode\" content=\"" + writingmode + "\"/>\n",
                      "<meta name=\"zero-gutter\" content=\"true\"/>\n",
                      "<meta name=\"zero-margin\" content=\"true\"/>\n",
                      "<meta name=\"ke-border-color\" content=\"#FFFFFF\"/>\n",
                      "<meta name=\"ke-border-width\" content=\"0\"/>\n"])
        if options.kfx:
            f.writelines(["<meta name=\"orientation-lock\" content=\"none\"/>\n",
                          "<meta name=\"region-mag\" content=\"false\"/>\n"])
        else:
            f.writelines(["<meta name=\"orientation-lock\" content=\"portrait\"/>\n",
                          "<meta name=\"region-mag\" content=\"true\"/>\n"])
    else:
        f.writelines(["<meta property=\"rendition:orientation\">portrait</meta>\n",
                      "<meta property=\"rendition:spread\">portrait</meta>\n",
                      "<meta property=\"rendition:layout\">pre-paginated</meta>\n"])
    f.writelines(["</metadata>\n<manifest>\n<item id=\"ncx\" href=\"toc.ncx\" ",
                  "media-type=\"application/x-dtbncx+xml\"/>\n",
                  "<item id=\"nav\" href=\"nav.xhtml\" ",
                  "properties=\"nav\" media-type=\"application/xhtml+xml\"/>\n"])
    if cover is not None:
        filename = getImageFileName(cover.replace(os.path.join(dstdir, 'OEBPS'), '').lstrip('/').lstrip('\\\\'))
        if '.png' == filename[1]:
            mt = 'image/png'
        else:
            mt = 'image/jpeg'
        f.write("<item id=\"cover\" href=\"Images/cover" + filename[1] + "\" media-type=\"" + mt +
                "\" properties=\"cover-image\"/>\n")
    reflist = []
    for path in filelist:
        folder = path[0].replace(os.path.join(dstdir, 'OEBPS'), '').lstrip('/').lstrip('\\\\').replace("\\", "/")
        filename = getImageFileName(path[1])
        uniqueid = os.path.join(folder, filename[0]).replace('/', '_').replace('\\', '_')
        reflist.append(uniqueid)
        f.write("<item id=\"page_" + str(uniqueid) + "\" href=\"" +
                folder.replace('Images', 'Text') + "/" + filename[0] +
                ".xhtml\" media-type=\"application/xhtml+xml\"/>\n")
        if '.png' == filename[1]:
            mt = 'image/png'
        else:
            mt = 'image/jpeg'
        f.write("<item id=\"img_" + str(uniqueid) + "\" href=\"" + folder + "/" + path[1] + "\" media-type=\"" +
                mt + "\"/>\n")
    f.write("<item id=\"css\" href=\"Text/style.css\" media-type=\"text/css\"/>\n")
    if options.righttoleft:
        f.write("</manifest>\n<spine page-progression-direction=\"rtl\" toc=\"ncx\">\n")
        pageside = "right"
    else:
        f.write("</manifest>\n<spine page-progression-direction=\"ltr\" toc=\"ncx\">\n")
        pageside = "left"
    if options.iskindle:
        for entry in reflist:
            if options.righttoleft:
                if entry.endswith("-b"):
                    f.write("<itemref idref=\"page_" + entry + "\" linear=\"yes\" properties=\"page-spread-right\"/>\n")
                    pageside = "right"
                elif entry.endswith("-c"):
                    f.write("<itemref idref=\"page_" + entry + "\" linear=\"yes\" properties=\"page-spread-left\"/>\n")
                    pageside = "right"
                else:
                    f.write("<itemref idref=\"page_" + entry + "\" linear=\"yes\" properties=\"page-spread-" +
                            pageside + "\"/>\n")
                    if pageside == "right":
                        pageside = "left"
                    else:
                        pageside = "right"
            else:
                if entry.endswith("-b"):
                    f.write("<itemref idref=\"page_" + entry + "\" linear=\"yes\" properties=\"page-spread-left\"/>\n")
                    pageside = "left"
                elif entry.endswith("-c"):
                    f.write("<itemref idref=\"page_" + entry + "\" linear=\"yes\" properties=\"page-spread-right\"/>\n")
                    pageside = "left"
                else:
                    f.write("<itemref idref=\"page_" + entry + "\" linear=\"yes\" properties=\"page-spread-" +
                            pageside + "\"/>\n")
                if pageside == "right":
                    pageside = "left"
                else:
                    pageside = "right"
    else:
        for entry in reflist:
            f.write("<itemref idref=\"page_" + entry + "\"/>\n")
    f.write("</spine>\n</package>\n")
    f.close()
    os.mkdir(os.path.join(dstdir, 'META-INF'))
    f = open(os.path.join(dstdir, 'META-INF', 'container.xml'), 'w', encoding='UTF-8')
    f.writelines(["<?xml version=\"1.0\"?>\n",
                  "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">\n",
                  "<rootfiles>\n",
                  "<rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/>\n",
                  "</rootfiles>\n",
                  "</container>"])
    f.close()


def buildEPUB(path, chapternames, tomenumber):
    filelist = []
    chapterlist = []
    cover = None
    os.mkdir(os.path.join(path, 'OEBPS', 'Text'))
    f = open(os.path.join(path, 'OEBPS', 'Text', 'style.css'), 'w', encoding='UTF-8')
    f.writelines(["@page {\n",
                  "margin: 0;\n",
                  "}\n",
                  "body {\n",
                  "display: block;\n",
                  "margin: 0;\n",
                  "padding: 0;\n",
                  "}\n"])
    if options.iskindle and options.panelview:
        f.writelines(["#PV {\n",
                      "position: absolute;\n",
                      "width: 100%;\n",
                      "height: 100%;\n",
                      "top: 0;\n",
                      "left: 0;\n",
                      "}\n",
                      "#PV-T {\n",
                      "top: 0;\n",
                      "width: 100%;\n",
                      "height: 50%;\n",
                      "}\n",
                      "#PV-B {\n",
                      "bottom: 0;\n",
                      "width: 100%;\n",
                      "height: 50%;\n",
                      "}\n",
                      "#PV-L {\n",
                      "left: 0;\n",
                      "width: 49.5%;\n",
                      "height: 100%;\n",
                      "float: left;\n",
                      "}\n",
                      "#PV-R {\n",
                      "right: 0;\n",
                      "width: 49.5%;\n",
                      "height: 100%;\n",
                      "float: right;\n",
                      "}\n",
                      "#PV-TL {\n",
                      "top: 0;\n",
                      "left: 0;\n",
                      "width: 49.5%;\n",
                      "height: 50%;\n",
                      "float: left;\n",
                      "}\n",
                      "#PV-TR {\n",
                      "top: 0;\n",
                      "right: 0;\n",
                      "width: 49.5%;\n",
                      "height: 50%;\n",
                      "float: right;\n",
                      "}\n",
                      "#PV-BL {\n",
                      "bottom: 0;\n",
                      "left: 0;\n",
                      "width: 49.5%;\n",
                      "height: 50%;\n",
                      "float: left;\n",
                      "}\n",
                      "#PV-BR {\n",
                      "bottom: 0;\n",
                      "right: 0;\n",
                      "width: 49.5%;\n",
                      "height: 50%;\n",
                      "float: right;\n",
                      "}\n",
                      ".PV-P {\n",
                      "width: 100%;\n",
                      "height: 100%;\n",
                      "top: 0;\n",
                      "position: absolute;\n",
                      "display: none;\n",
                      "}\n"])
    f.close()
    for dirpath, dirnames, filenames in os.walk(os.path.join(path, 'OEBPS', 'Images')):
        chapter = False
        dirnames, filenames = walkSort(dirnames, filenames)
        for afile in filenames:
            filelist.append(buildHTML(dirpath, afile, os.path.join(dirpath, afile)))
            if not chapter:
                chapterlist.append((dirpath.replace('Images', 'Text'), filelist[-1][1]))
                chapter = True
            if cover is None:
                cover = os.path.join(os.path.join(path, 'OEBPS', 'Images'),
                                     'cover' + getImageFileName(filelist[-1][1])[1])
                options.covers.append((image.Cover(os.path.join(filelist[-1][0], filelist[-1][1]), cover, options,
                                                   tomenumber), options.uuid))
    # Overwrite chapternames if tree is flat and ComicInfo.xml has bookmarks
    if not chapternames and options.chapters:
        chapterlist = []
        globaldiff = 0
        for aChapter in options.chapters:
            pageid = aChapter[0]
            for x in range(0, pageid + globaldiff + 1):
                if '-kcc-b' in filelist[x][1]:
                    pageid += 1
            if '-kcc-c' in filelist[pageid][1]:
                pageid -= 1
            filename = filelist[pageid][1]
            chapterlist.append((filelist[pageid][0].replace('Images', 'Text'), filename))
            chapternames[filename] = aChapter[1]
            globaldiff = pageid - (aChapter[0] + globaldiff)
    buildNCX(path, options.title, chapterlist, chapternames)
    buildNAV(path, options.title, chapterlist, chapternames)
    buildOPF(path, options.title, filelist, cover)


def imgDirectoryProcessing(path):
    global workerPool, workerOutput
    workerPool = Pool(maxtasksperchild=100)
    workerOutput = []
    options.imgMetadata = {}
    options.imgOld = []
    work = []
    pagenumber = 0
    for dirpath, _, filenames in os.walk(path):
        for afile in filenames:
            pagenumber += 1
            if not afile == "ComicInfo.xml":
                work.append([afile, dirpath, options])
    if GUI:
        GUI.progressBarTick.emit(str(pagenumber))
    if len(work) > 0:
        for i in work:
            workerPool.apply_async(func=imgFileProcessing, args=(i, ), callback=imgFileProcessingTick)
        workerPool.close()
        workerPool.join()
        if GUI and not GUI.conversionAlive:
            rmtree(os.path.join(path, '..', '..'), True)
            raise UserWarning("Conversion interrupted.")
        if len(workerOutput) > 0:
            rmtree(os.path.join(path, '..', '..'), True)
            raise RuntimeError("One of workers crashed. Cause: " + workerOutput[0][0], workerOutput[0][1])
        for file in options.imgOld:
            if os.path.isfile(file):
                os.remove(file)
    else:
        rmtree(os.path.join(path, '..', '..'), True)
        raise UserWarning("Source directory is empty.")


def imgFileProcessingTick(output):
    if isinstance(output, tuple):
        workerOutput.append(output)
        workerPool.terminate()
    else:
        for page in output:
            if page is not None:
                options.imgMetadata[page[0]] = page[1]
                options.imgOld.append(page[2])
    if GUI:
        GUI.progressBarTick.emit('tick')
        if not GUI.conversionAlive:
            workerPool.terminate()


def imgFileProcessing(work):
    try:
        afile = work[0]
        dirpath = work[1]
        opt = work[2]
        output = []
        workImg = image.ComicPageParser((dirpath, afile), opt)
        for i in workImg.payload:
            img = image.ComicPage(opt, *i)
            if opt.cropping == 2 and not opt.webtoon:
                img.cropPageNumber(opt.croppingp, opt.croppingm)
            if opt.cropping > 0 and not opt.webtoon:
                img.cropMargin(opt.croppingp, opt.croppingm)
            img.autocontrastImage()
            img.resizeImage()
            if opt.forcepng and not opt.forcecolor:
                img.quantizeImage()
            output.append(img.saveToDir())
        return output
    except Exception:
        return str(sys.exc_info()[1]), sanitizeTrace(sys.exc_info()[2])


def getExtension():
    if options.format == "CBZ":
        ext = ".cbz"
    elif options.format == "MOBI":
        ext = ".mobi"
    else:
        ext = ".epub"
    return ext


def getOutputFilename(srcpath, output, ext, tomenumber, checkexists=False):
    if options.copysourcetree:
        copysourcetree = options.copysourcetree
        if copysourcetree.endswith("/") or copysourcetree.endswith("\\"):
            copysourcetree = os.path.split(copysourcetree)[0]
        copysourcetree = os.path.basename(copysourcetree) + os.path.split(
                                    str(srcpath).split(copysourcetree)[-1])[0] + os.sep
    else:
        copysourcetree = ""
    if options.padzeros > 0:
        padzeros = options.padzeros + 1
    else: padzeros = 0
    if srcpath[-1] == os.path.sep:
        srcpath = srcpath[:-1]
    if 'Ko' in options.profile and options.format == 'EPUB':
        ext = '.kepub.epub'
    if output is not None:
        if output.endswith(ext):
            filename = os.path.abspath(output)
        elif os.path.isdir(srcpath):
            filename = os.path.join(os.path.abspath(output), copysourcetree, os.path.basename(srcpath) + ext)
        else:
            filename = os.path.join(os.path.abspath(output), copysourcetree,
                                    os.path.basename(os.path.splitext(srcpath)[0]) + ext)
    elif os.path.isdir(srcpath):
        filename = srcpath + tomenumber.zfill(padzeros) + ext
    else:
        if 'Ko' in options.profile and options.format == 'EPUB':
            path = srcpath.split(os.path.sep)
            path[-1] = ''.join(e for e in path[-1].split('.')[0] if e.isalnum()) + tomenumber + ext
            if not path[-1].split('.')[0]:
                path[-1] = 'KCCPlaceholder' + tomenumber + ext
            filename = os.path.sep.join(path)
        else:
            filename = os.path.splitext(srcpath)[0] + tomenumber + ext
    if checkexists == False:
        if os.path.isfile(filename):
            counter = 0
            basename = os.path.splitext(filename)[0]
            while os.path.isfile(basename + '_kcc' + str(counter).zfill(padzeros) + ext):
                counter += 1
            filename = basename + '_kcc' + str(counter).zfill(padzeros) + ext
    return filename


def getComicInfo(path, originalpath):
    xmlPath = os.path.join(path, 'ComicInfo.xml')
    options.authors = ['KCC']
    options.chapters = []
    options.summary = ''
    titleSuffix = ''
    if options.title == 'defaulttitle':
        defaultTitle = True
        if os.path.isdir(originalpath):
            options.title = os.path.basename(originalpath)
        else:
            options.title = os.path.splitext(os.path.basename(originalpath))[0]
    else:
        defaultTitle = False
    if os.path.exists(xmlPath):
        try:
            xml = metadata.MetadataParser(xmlPath)
        except Exception:
            os.remove(xmlPath)
            return
        options.authors = []
        if defaultTitle:
            if xml.data['Series']:
                options.title = hescape(xml.data['Series'])
            if xml.data['Volume']:
                titleSuffix += ' V' + xml.data['Volume'].zfill(2)
            if xml.data['Number']:
                titleSuffix += ' #' + xml.data['Number'].zfill(3)
            options.title += titleSuffix
        for field in ['Writers', 'Pencillers', 'Inkers', 'Colorists']:
            for person in xml.data[field]:
                options.authors.append(hescape(person))
        if len(options.authors) > 0:
            options.authors = list(set(options.authors))
            options.authors.sort()
        else:
            options.authors = ['KCC']
        if xml.data['Bookmarks']:
            options.chapters = xml.data['Bookmarks']
        if xml.data['Summary']:
            options.summary = hescape(xml.data['Summary'])
        if not options.copycomicinfo:
            os.remove(xmlPath)


def getTopMargin(deviceres, size):
    y = int((deviceres[1] - size[1]) / 2) / deviceres[1] * 100
    return str(round(y, 1))


def getPanelViewResolution(imagesize, deviceres):
    scale = float(deviceres[0]) / float(imagesize[0])
    return int(deviceres[0]), int(scale * imagesize[1])


def getPanelViewSize(deviceres, size):
    x = int(deviceres[0] / 2 - size[0] / 2) / deviceres[0] * 100
    y = int(deviceres[1] / 2 - size[1] / 2) / deviceres[1] * 100
    return str(int(x)), str(int(y))


def sanitizeTree(filetree):
    chapterNames = {}
    for root, dirs, files in os.walk(filetree, False):
        for name in files:
            if not name == "ComicInfo.xml":
                splitname = os.path.splitext(name)
                slugified = slugify(splitname[0], False)
                while os.path.exists(os.path.join(root, slugified + splitname[1])) and splitname[0].upper()\
                        != slugified.upper():
                    slugified += "A"
                newKey = os.path.join(root, slugified + splitname[1])
                key = os.path.join(root, name)
                if key != newKey:
                    os.replace(key, newKey)
        for name in dirs:
            tmpName = name
            slugified = slugify(name, True)
            while os.path.exists(os.path.join(root, slugified)) and name.upper() != slugified.upper():
                slugified += "A"
            chapterNames[slugified] = tmpName
            newKey = os.path.join(root, slugified)
            key = os.path.join(root, name)
            if key != newKey:
                os.replace(key, newKey)
    return chapterNames


def sanitizeTreeKobo(filetree):
    pageNumber = 0
    for root, dirs, files in os.walk(filetree):
        dirs, files = walkSort(dirs, files)
        for name in files:
            if not name == "ComicInfo.xml":
                splitname = os.path.splitext(name)
                slugified = str(pageNumber).zfill(5)
                pageNumber += 1
                while os.path.exists(os.path.join(root, slugified + splitname[1])) and splitname[0].upper()\
                        != slugified.upper():
                    slugified += "A"
                newKey = os.path.join(root, slugified + splitname[1])
                key = os.path.join(root, name)
                if key != newKey:
                    os.replace(key, newKey)


def splitDirectory(path):
    level = -1
    for root, _, files in os.walk(os.path.join(path, 'OEBPS', 'Images')):
        for f in files:
            if f.endswith('.jpg') or f.endswith('.jpeg') or f.endswith('.png') or f.endswith('.gif') or \
                    f.endswith('.webp'):
                newLevel = os.path.join(root, f).replace(os.path.join(path, 'OEBPS', 'Images'), '').count(os.sep)
                if level != -1 and level != newLevel:
                    level = 0
                    break
                else:
                    level = newLevel
    if level > 0:
        splitter = splitProcess(os.path.join(path, 'OEBPS', 'Images'), level)
        path = [path]
        for tome in splitter:
            path.append(tome)
        return path
    else:
        raise UserWarning('Unsupported directory structure.')


def splitProcess(path, mode):
    output = []
    currentSize = 0
    currentTarget = path
    if options.targetsize:
        targetSize = options.targetsize * 1048576
    elif options.webtoon:
        targetSize = 104857600
    else:
        targetSize = 419430400
    if options.batchsplit == 2 and mode == 2:
        mode = 3
    if mode < 3:
        for root, dirs, files in walkLevel(path, 0):
            for name in files if mode == 1 else dirs:
                if mode == 1:
                    size = os.path.getsize(os.path.join(root, name))
                else:
                    size = getDirectorySize(os.path.join(root, name))
                if currentSize + size > targetSize:
                    currentTarget, pathRoot = createNewTome()
                    output.append(pathRoot)
                    currentSize = size
                else:
                    currentSize += size
                if path != currentTarget:
                    move(os.path.join(root, name), os.path.join(currentTarget, name))
    else:
        firstTome = True
        for root, dirs, _ in walkLevel(path, 0):
            for name in dirs:
                if not firstTome:
                    currentTarget, pathRoot = createNewTome()
                    output.append(pathRoot)
                    move(os.path.join(root, name), os.path.join(currentTarget, name))
                else:
                    firstTome = False
    return output


def detectCorruption(tmppath, orgpath):
    imageNumber = 0
    imageSmaller = 0
    alreadyProcessed = False
    for root, _, files in os.walk(tmppath, False):
        for name in files:
            if getImageFileName(name) is not None:
                if not alreadyProcessed and getImageFileName(name)[0].endswith('-kcc'):
                    alreadyProcessed = True
                path = os.path.join(root, name)
                pathOrg = orgpath + path.split('OEBPS' + os.path.sep + 'Images')[1]
                if os.path.getsize(path) == 0:
                    rmtree(os.path.join(tmppath, '..', '..'), True)
                    raise RuntimeError('Image file %s is corrupted.' % pathOrg)
                try:
                    img = Image.open(path)
                    img.verify()
                    img = Image.open(path)
                    img.load()
                    imageNumber += 1
                    if options.profileData[1][0] > img.size[0] and options.profileData[1][1] > img.size[1]:
                        imageSmaller += 1
                except Exception as err:
                    rmtree(os.path.join(tmppath, '..', '..'), True)
                    if 'decoder' in str(err) and 'not available' in str(err):
                        raise RuntimeError('Pillow was compiled without JPG and/or PNG decoder.')
                    else:
                        raise RuntimeError('Image file %s is corrupted. Error: %s' % (pathOrg, str(err)))
            elif options.copycomicinfo and name == "ComicInfo.xml":
                pass
            else:
                os.remove(os.path.join(root, name))
    if alreadyProcessed:
        if options.skipexisting > 1:
            alreadyprocessedlist.append(os.path.normpath(orgpath))
            if options.skipexisting == 2 or options.skipexisting == 4:
                print("File(s) were probably created by KCC. Skipping operation.")
                if GUI:
                    GUI.addMessage.emit('File(s) were probably created by KCC. Skipping operation.'
                                        , 'warning', False)
                    GUI.addMessage.emit('', '', False)
                return True
        else:
            print("WARNING: Source file(s) were probably created by KCC. The second conversion will decrease quality.")
            multiprocessedlist.append(os.path.normpath(getOutputFilename(
                    orgpath, options.output, getExtension(), '', checkexists=True)))
            if GUI:
                GUI.addMessage.emit('Source file(s) were probably created by KCC. The second conversion will decrease quality.'
                                    , 'warning', False)
                GUI.addMessage.emit('', '', False)
    if imageSmaller > imageNumber * 0.25 and not options.upscale and not options.stretch:
        print("WARNING: More than 25% of images are smaller than target device resolution. "
              "Consider enabling stretching or upscaling to improve readability.")
        if GUI:
            GUI.addMessage.emit('More than 25% of images are smaller than target device resolution.', 'warning', False)
            GUI.addMessage.emit('Consider enabling stretching or upscaling to improve readability.', 'warning', False)
            GUI.addMessage.emit('', '', False)


def createNewTome():
    tomePathRoot = mkdtemp('', 'KCC-')
    tomePath = os.path.join(tomePathRoot, 'OEBPS', 'Images')
    os.makedirs(tomePath)
    return tomePath, tomePathRoot


def slugify(value, isdir):
    if isdir:
        value = slugifyExt(value, regex_pattern=r'[^-a-z0-9_\.]+').strip('.')
    else:
        value = slugifyExt(value).strip('.')
    value = sub(r'0*([0-9]{4,})', r'\1', sub(r'([0-9]+)', r'0000\1', value, count=2))
    return value


def makeZIP(zipfilename, basedir, isepub=False):
    zipfilename = os.path.abspath(zipfilename) + '.zip'
    zipOutput = ZipFile(zipfilename, 'w', ZIP_DEFLATED)
    if isepub:
        zipOutput.writestr('mimetype', 'application/epub+zip', ZIP_STORED)
    for dirpath, _, filenames in os.walk(basedir):
        for name in filenames:
            path = os.path.normpath(os.path.join(dirpath, name))
            aPath = os.path.normpath(os.path.join(dirpath.replace(basedir, ''), name))
            if os.path.isfile(path):
                zipOutput.write(path, aPath)
    zipOutput.close()
    return zipfilename


def makeParser():
    psr = argparse.ArgumentParser(prog="kcc-c2e", usage="kcc-c2e [options] [input]", add_help =False)

    mandatoryOptions = psr.add_argument_group("MANDATORY")
    mainOptions = psr.add_argument_group("MAIN")
    processingOptions = psr.add_argument_group("PROCESSING")
    outputOptions = psr.add_argument_group("OUTPUT SETTINGS")
    customProfileOptions = psr.add_argument_group("CUSTOM PROFILE")
    otherOptions = psr.add_argument_group("OTHER")
    profiles = image.ProfileData().getRows("Profile")
    formats = ["Auto", "MOBI", "EPUB", "CBZ", "KFX"]

    mandatoryOptions.add_argument("input", action="extend", nargs="*", default=None,
                                 help="Full path to comic folder(s) or file(s) to be proccessed. Separate multiple inputs with"
                                 " spaces.")

    mainOptions.add_argument("-p", "--profile", metavar="PROFILE", action="store", dest="profile", default="KV", choices=profiles,
                             help="Device profile (Common options: K578, KPW5, KV, KoGHD, KoA, KoAHD, KoAH2O, KoAO, KoC, KoL,"
                             " KoF, KoN, KoE, KoS). For a list of all avaliable profiles, type -h profile [Default=%(default)s]")
    mainOptions.add_argument("-m", "--manga-style", action="store_true", dest="righttoleft", default=False,
                             help="Manga style (right-to-left reading and splitting)")
    mainOptions.add_argument("-q", "--hq", action="store_true", dest="hq", default=False,
                             help="Try to increase the quality of magnification")
    mainOptions.add_argument("-2", "--two-panel", action="store_true", dest="autoscale", default=False,
                             help="Display two not four panels in Panel View mode")
    mainOptions.add_argument("-w", "--webtoon", action="store_true", dest="webtoon", default=False,
                             help="Webtoon processing mode"),
    mainOptions.add_argument("--ts","--targetsize", type=int, dest="targetsize", default=None,
                           help="the maximal size of output file in MB."
                                " [Default=100MB for webtoon and 400MB for others]")

    outputOptions.add_argument("-o", "--output", action="store", dest="output", default=None,
                               help="Output generated file(s) to specified directory or file")
    outputOptions.add_argument("--cst", "--copysourcetree", action="store", dest="copysourcetree", default=None,
                               help="Additional option for use with --output. Name of the top most directory"
                               " or full path to the directory to be used when recreating the source directory"
                               " tree in the output directory.")
    outputOptions.add_argument("-t", "--title", action="store", dest="title", default="defaulttitle",
                               help="Comic title [Default=filename or directory name]")
    outputOptions.add_argument("-f", "--format", action="store", dest="format", default="Auto", choices=formats,
                               help="Output format (Available options: Auto, MOBI, EPUB, CBZ, KFX) [Default=%(default)s]")
    outputOptions.add_argument("-b", "--batchsplit", type=int, dest="batchsplit", default="0", choices=range(0, 3),
                               help="Split output into multiple files. 0: Don't split 1: Automatic mode "
                               "2: Consider every subdirectory as separate volume [Default=%(default)s]")
    outputOptions.add_argument("-e", "--skipexisting", type=int, dest="skipexisting", default="0", choices=range(0, 6),
                               help="Skip processing specific files. 0: Do not skip. 1: Skip if the wanted file already"
                               " exists in the output directory. 2: Skip if the source file was already processed."
                               " 3: Copy the already processed file to the output directory. 4: Use both options 1 and 2."
                               " 5: Use both options 1 and 3. [Default=%(default)s]")
    outputOptions.add_argument("-z", "--padzeros", type=int, dest="padzeros", default="0",
                               help="Pad \"_kcc(#)\" with given number of zeros. [Default=%(default)s]")
    outputOptions.add_argument("--cci", "--copycomicinfo", action="store_true", dest="copycomicinfo", default=False,
                               help="Copy ComicInfo.xml to generated file")

    processingOptions.add_argument("-n", "--noprocessing", action="store_true", dest="noprocessing", default=False,
                                   help="Do not modify image and ignore any profile or processing option")
    processingOptions.add_argument("-u", "--upscale", action="store_true", dest="upscale", default=False,
                                   help="Resize images smaller than device's resolution")
    processingOptions.add_argument("-s", "--stretch", action="store_true", dest="stretch", default=False,
                                   help="Stretch images to device's resolution")
    processingOptions.add_argument("--ns","--noshrink", action="store_true", dest="noshrink", default=False,
                                 help="Add borders or stretch the image to fit device ratio instead of shrinking the"
                                 " image.")
    processingOptions.add_argument("-r", "--splitter", type=int, dest="splitter", default="0", choices=range(0, 3),
                                   help="Double page parsing mode. 0: Split 1: Rotate 2: Both [Default=%(default)s]")
    processingOptions.add_argument("-g", "--gamma", type=float, dest="gamma", default="0.0",
                                   help="Apply gamma correction to linearize the image [Default=Auto]")
    processingOptions.add_argument("-c", "--cropping", type=int, dest="cropping", default="2", choices=range(0, 3),
                                   help="Set cropping mode. 0: Disabled 1: Margins 2: Margins + page numbers"
                                   " [Default=%(default)s]")
    processingOptions.add_argument("--cp", "--croppingpower",metavar="CROPPINGPOWER", type=float, dest="croppingp",
                                   default="1.0", help="Set cropping power [Default=%(default)s]")
    processingOptions.add_argument("--cm", "--croppingminimum", metavar="CROPPINGMINIMUM", type=float, dest="croppingm",
                                   default="0.0", help="Set cropping minimum area ratio [Default=0.0]")
    processingOptions.add_argument("-bc", "--bordercolor", metavar="BORDERCOLOR", action="store", dest="bordersColor",
                                   default=None, help="Color of borders. Either use one of the available named colors or "
                                   " use the hexadecimal value of the color. For a list of all avaliable named colors,"
                                   " type -h bordercolor. [Default=Auto]")
    processingOptions.add_argument("--fc", "--forcecolor", action="store_true", dest="forcecolor", default=False,
                                   help="Don't convert images to grayscale")
    processingOptions.add_argument("--fp", "--forcepng", action="store_true", dest="forcepng", default=False,
                                   help="Create PNG files instead JPEG")
    processingOptions.add_argument("--mj", "--mozjpeg", action="store_true", dest="mozjpeg", default=False,
                                   help="Create JPEG files using mozJpeg")

    customProfileOptions.add_argument("--cw", "--customwidth", type=int, dest="customwidth", default="0",
                                      help="Replace screen width provided by device profile")
    customProfileOptions.add_argument("--ch", "--customheight", type=int, dest="customheight", default="0",
                                      help="Replace screen height provided by device profile")

    otherOptions.add_argument("-h", "--help", action="extend", nargs="*", default=None,
                              help="Show this help message and exit")

    return psr


def optionsHelp():
    if options.help[0] == "profile":
        print(image.ProfileData().getAllProfiles())
    elif options.help[0] == "bordercolor":
        import pandas as pd
        namedcolors = pd.DataFrame(ImageColor.colormap.items(), columns=['Named Color', 'Hex Value'])
        pd.set_option('display.max_rows', None)
        print()
        print(namedcolors)
        print("Note: Refer here to see the colors visualized: "
                " https://drafts.csswg.org/css-color-4/#named-colors")
    else:
        print("ERROR: Help option " + str(options.help) + " not avaliable.")


def checkOptions():
    global options
    profilematch = image.ProfileData().checkProfileMatch
    options.panelview = True
    options.iskindle = False
    options.kfx = False
    if options.format == 'Auto':
        if not options.profile in ['KDX'] and \
                profilematch(["Profile", options.profile], ["Manufacturer", "Kindle"]):
            options.format = 'MOBI'
        elif options.profile in ['OTHER'] or \
                profilematch(["Profile", options.profile], ["Manufacturer", "Kobo"]) or \
                profilematch(["Profile", options.profile], ["Manufacturer", "Nook"]) or \
                profilematch(["Profile", options.profile], ["Manufacturer", "Pocketbook"]) or \
                profilematch(["Profile", options.profile], ["Manufacturer", "Tolino"]):
            options.format = 'EPUB'
        elif options.profile in ['KDX'] or \
                profilematch(["Profile", options.profile], ["Manufacturer", "Amazon"]) or \
                profilematch(["Profile", options.profile], ["Manufacturer", "Apple"]):
            options.format = 'CBZ'
        else:
            raise UserWarning ("ERROR: Profile " + options.profile + " does not support Auto format. Specify a"
                               " format with the format option.")
    if profilematch(["Profile", options.profile], ["Manufacturer","Kindle"]):
        options.iskindle = True
    # Splitting MOBI is not optional
    if (options.format == 'MOBI' or options.format == 'KFX') and options.batchsplit != 2:
        options.batchsplit = 1
    # Older Kindle models don't support Panel View.
    if options.profile == 'K1' or options.profile == 'K2' or options.profile == 'K34' or options.profile == 'KDX':
        options.panelview = False
        options.hq = False
    # Webtoon mode mandatory options
    if options.webtoon:
        options.panelview = False
        options.righttoleft = False
        options.upscale = True
        options.hq = False
    # Disable all Kindle features for other e-readers
    if options.profile == 'OTHER':
        options.panelview = False
        options.hq = False
    if 'Ko' in options.profile:
        options.panelview = False
        options.hq = False
    # CBZ files on Kindle DX/DXG support higher resolution
    if options.profile == 'KDX' and options.format == 'CBZ':
        options.customheight = 1200
    # KFX output create EPUB that might be can be by jhowell KFX Output Calibre plugin
    if options.format == 'KFX':
        options.format = 'EPUB'
        options.kfx = True
        options.panelview = False
    # Override profile data
    if options.customwidth != 0 or options.customheight != 0:
        X = image.ProfileData().profiles(options.profile)[1][0]
        Y = image.ProfileData().profiles(options.profile)[1][1]
        if options.customwidth != 0:
            X = options.customwidth
        if options.customheight != 0:
            Y = options.customheight
        newProfile = ("Custom", (int(X), int(Y)), image.ProfileData.Palette16,
                      image.ProfileData().profiles(options.profile)[3])
        # image.ProfileData.Profiles["Custom"] = newProfile
        options.profile = "Custom"
        options.profileData = newProfile
    else:
        options.profileData = image.ProfileData().profiles(options.profile)
    # Only copy ComicInfo.xml to .cbz files
    if not options.format == "CBZ" and options.copycomicinfo:
        raise UserWarning("ERROR: Can only copy ComicInfo.xml to CBZ format. Either change format or don't use the"
                          " copycomicinfo option.")
    # Only allow named color or hexadecimal border color
    if options.bordersColor:
        if not options.bordersColor in ImageColor.colormap.keys() and \
                not compile(r"^#?([0-9a-f]{3}){1,2}$").match(options.bordersColor):
            raise UserWarning("ERROR: Border color must be a hexadecimal color or one of the named colors.")


def checkTools(source):
    source = source.upper()
    if source.endswith('.CB7') or source.endswith('.7Z') or source.endswith('.RAR') or source.endswith('.CBR') or \
            source.endswith('.ZIP') or source.endswith('.CBZ'):
        process = Popen('7z', stdout=PIPE, stderr=STDOUT, stdin=PIPE, shell=True)
        process.communicate()
        if process.returncode != 0 and process.returncode != 7:
            print('ERROR: 7z is missing!')
            exit(1)
    if options.format == 'MOBI':
        kindleGenExitCode = Popen('kindlegen -locale en', stdout=PIPE, stderr=STDOUT, stdin=PIPE, shell=True)
        kindleGenExitCode.communicate()
        if kindleGenExitCode.returncode != 0:
            print('ERROR: KindleGen is missing!')
            exit(1)


def checkPre(source):
    # Make sure that all temporary files are gone
    for root, dirs, _ in walkLevel(gettempdir(), 0):
        for tempdir in dirs:
            if tempdir.startswith('KCC-'):
                rmtree(os.path.join(root, tempdir), True)
    # Make sure that target directory is writable
    if os.path.isdir(source):
        src = os.path.abspath(os.path.join(source, '..'))
    else:
        src = os.path.dirname(source)
    try:
        with TemporaryFile(prefix='KCC-', dir=src):
            pass
    except Exception:
        raise UserWarning("Target directory is not writable.")
    if options.skipexisting > 0:
        if options.format == "CBZ":
            ext = ".cbz"
        else:
            ext = ".epub"
        filepath = getOutputFilename(source, options.output, ext, '', checkexists=True)
        if options.skipexisting == 1 or options.skipexisting == 4 or options.skipexisting == 5:
            if os.path.isfile(filepath):
                print("File already exists. Skipping operation.")
                alreadyexistslist.append(os.path.normpath(source))
                return True
        if "_kcc" in os.path.basename(filepath):
            if options.skipexisting == 2 or options.skipexisting == 4:
                print("File(s) were probably created by KCC. Skipping operation.")
                alreadyprocessedlist.append(os.path.normpath(source))
                return True
            elif options.skipexisting == 3 or options.skipexisting == 5:
                print("File(s) were probably created by KCC. Copying to output directory.")
                copyprocessedlist.append(os.path.normpath(filepath))
                copyfile(source,filepath)
                return True


def checkExists(source):
    if options.skipexisting == 1 or options.skipexisting == 4:
        if options.format == "CBZ":
            ext = ".cbz"
        elif options.format == "MOBI":
            ext = ".mobi"
        else:
            ext = ".epub"
        filepath = getOutputFilename(source, options.output, ext, '', checkexists=True)
        if os.path.isfile(filepath):
            return filepath


def makeBook(source, qtgui=None):
    global GUI
    GUI = qtgui
    if GUI:
        GUI.progressBarTick.emit('1')
    else:
        checkTools(source)
    if not checkPre(source):
        print("Preparing source images...")
        path = getWorkFolder(source, "KCC-")
        print("Checking images...")
        getComicInfo(os.path.join(path, "OEBPS", "Images"), source)
        if not detectCorruption(os.path.join(path, "OEBPS", "Images"), source):
            if options.webtoon:
                y = image.ProfileData().profiles(options.profile)[1][1]
                comic2panel.main(['-y ' + str(y), '-i', '-m', path], qtgui)
            if options.noprocessing:
                print("Do not process image. Ignore any profile or processing option.")
            elif options.skipexisting == 3 and os.path.normpath(source) in alreadyprocessedlist or \
                    options.skipexisting == 5 and os.path.normpath(source) in alreadyprocessedlist:
                print("File was probably created by KCC. Copying to output directory.")
                copyprocessedlist.append(os.path.normpath(getOutputFilename(
                    source, options.output, getExtension(), '', checkexists=True)))
                try:
                    alreadyprocessedlist.pop()
                except:
                    pass
            else:
                print("Processing images...")
                if GUI:
                    GUI.progressBarTick.emit('Processing images')
                imgDirectoryProcessing(os.path.join(path, "OEBPS", "Images"))
            if GUI:
                GUI.progressBarTick.emit('1')
            chapterNames = sanitizeTree(os.path.join(path, 'OEBPS', 'Images'))
            if 'Ko' in options.profile and options.format == 'CBZ':
                sanitizeTreeKobo(os.path.join(path, 'OEBPS', 'Images'))
            if options.batchsplit > 0:
                tomes = splitDirectory(path)
            else:
                tomes = [path]
            filepath = []
            tomeNumber = 0
            if GUI:
                if options.format == 'CBZ':
                    GUI.progressBarTick.emit('Compressing CBZ files')
                else:
                    GUI.progressBarTick.emit('Compressing EPUB files')
                GUI.progressBarTick.emit(str(len(tomes) + 1))
                GUI.progressBarTick.emit('tick')
            options.baseTitle = options.title
            options.covers = []
            for tome in tomes:
                options.uuid = str(uuid4())
                if len(tomes) > 9:
                    tomeNumber += 1
                    options.title = options.baseTitle + ' [' + str(tomeNumber).zfill(2) + '/' + \
                                    str(len(tomes)).zfill(2) + ']'
                elif len(tomes) > 1:
                    tomeNumber += 1
                    options.title = options.baseTitle + ' [' + str(tomeNumber) + '/' + str(len(tomes)) + ']'
                if options.format == 'CBZ':
                    print("Creating CBZ file...")
                    if len(tomes) > 1:
                        filepath.append(getOutputFilename(source, options.output, '.cbz', ' ' + str(tomeNumber)))
                    else:
                        filepath.append(getOutputFilename(source, options.output, '.cbz', ''))
                    makeZIP(tome + '_comic', os.path.join(tome, "OEBPS", "Images"))
                else:
                    print("Creating EPUB file...")
                    buildEPUB(tome, chapterNames, tomeNumber)
                    if len(tomes) > 1:
                        filepath.append(getOutputFilename(source, options.output, '.epub', ' ' + str(tomeNumber)))
                    else:
                        filepath.append(getOutputFilename(source, options.output, '.epub', ''))
                    makeZIP(tome + '_comic', tome, True)
                if not os.path.exists(os.path.split(filepath[-1])[0]):
                    try:
                        print("Recreating directory tree in ouput directory...")
                        os.makedirs(os.path.split(filepath[-1])[0])
                    except:
                        raise UserWarning("Unable to recreate the directory tree in the ouput directory.")
                copyfile(tome + '_comic.zip', filepath[-1])
                try:
                    os.remove(tome + '_comic.zip')
                except FileNotFoundError:
                    # newly temporary created file is not found. It might have been already deleted
                    pass
                if filepath and not os.path.normpath(filepath[-1]) in copyprocessedlist:
                    completedlist.append(filepath[-1])
                rmtree(tome, True)
                if GUI:
                    GUI.progressBarTick.emit('tick')
            if not GUI and options.format == 'MOBI':
                print("Creating MOBI files...")
                work = []
                for i in filepath:
                    work.append([i])
                output = makeMOBI(work, GUI)
                for errors in output:
                    if errors[0] != 0:
                        print('Error: KindleGen failed to create MOBI!')
                        print(errors)
                        return filepath
                k = kindle.Kindle()
                if k.path and k.coverSupport:
                    print("Kindle detected. Uploading covers...")
                for i in filepath:
                    output = makeMOBIFix(i, options.covers[filepath.index(i)][1])
                    if not output[0]:
                        print('Error: Failed to tweak KindleGen output!')
                        return filepath
                    else:
                        os.remove(i.replace('.epub', '.mobi') + '_toclean')
                    if k.path and k.coverSupport:
                        options.covers[filepath.index(i)][0].saveToKindle(k, options.covers[filepath.index(i)][1])
        else:
            rmtree(path, True)
            filepath = []
    else:
        filepath = checkExists(source)
    return filepath


def makeMOBIFix(item, uuid):
    os.remove(item)
    mobiPath = item.replace('.epub', '.mobi')
    move(mobiPath, mobiPath + '_toclean')
    try:
        dualmetafix.DualMobiMetaFix(mobiPath + '_toclean', mobiPath, bytes(uuid, 'UTF-8'))
        return [True]
    except Exception as err:
        return [False, format(err)]


def makeMOBIWorkerTick(output):
    makeMOBIWorkerOutput.append(output)
    if output[0] != 0:
        makeMOBIWorkerPool.terminate()
    if GUI:
        GUI.progressBarTick.emit('tick')
        if not GUI.conversionAlive:
            makeMOBIWorkerPool.terminate()


def makeMOBIWorker(item):
    item = item[0]
    kindlegenErrorCode = 0
    kindlegenError = ''
    try:
        if os.path.getsize(item) < 629145600:
            output = Popen('kindlegen -dont_append_source -locale en "' + item + '"',
                           stdout=PIPE, stderr=STDOUT, stdin=PIPE, shell=True)
            for line in output.stdout:
                line = line.decode('utf-8')
                # ERROR: Generic error
                if "Error(" in line:
                    kindlegenErrorCode = 1
                    kindlegenError = line
                # ERROR: EPUB too big
                if ":E23026:" in line:
                    kindlegenErrorCode = 23026
                if kindlegenErrorCode > 0:
                    break
                if ":I1036: Mobi file built successfully" in line:
                    output.terminate()
        else:
            # ERROR: EPUB too big
            kindlegenErrorCode = 23026
        return [kindlegenErrorCode, kindlegenError, item]
    except Exception as err:
        # ERROR: KCC unknown generic error
        kindlegenErrorCode = 1
        kindlegenError = format(err)
        return [kindlegenErrorCode, kindlegenError, item]


def makeMOBI(work, qtgui=None):
    global GUI, makeMOBIWorkerPool, makeMOBIWorkerOutput
    GUI = qtgui
    makeMOBIWorkerOutput = []
    availableMemory = virtual_memory().total / 1000000000
    if availableMemory <= 2:
        threadNumber = 1
    elif 2 < availableMemory <= 4:
        threadNumber = 2
    elif 4 < availableMemory:
        threadNumber = 4
    else:
        threadNumber = None
    makeMOBIWorkerPool = Pool(threadNumber, maxtasksperchild=10)
    for i in work:
        makeMOBIWorkerPool.apply_async(func=makeMOBIWorker, args=(i, ), callback=makeMOBIWorkerTick)
    makeMOBIWorkerPool.close()
    makeMOBIWorkerPool.join()
    return makeMOBIWorkerOutput
