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
import logging
from shutil import rmtree, copytree
from argparse import ArgumentParser
from multiprocessing import Pool
from PIL import Image, ImageChops, ImageOps, ImageDraw
from .shared import createLogger, getImageFileName, walkLevel, walkSort, sanitizeTrace, getWorkFolder, intro
try:
    from PyQt5 import QtCore
except ImportError:
    QtCore = None


def mergeDirectoryTick(output):
    if output:
        mergeWorkerOutput.append(output)
        mergeWorkerPool.terminate()
    if GUI:
        GUI.progressBarTick.emit('tick')
        if not GUI.conversionAlive:
            mergeWorkerPool.terminate()


def mergeDirectory(work):
    try:
        # backwards compatibility for Pillow <9.1.0
        if not hasattr(Image, 'Resampling'):
            Image.Resampling = Image
        directory = work[0]
        images = []
        imagesValid = []
        sizes = []
        targetHeight = 0
        for root, _, files in walkLevel(directory, 0):
            for name in files:
                if getImageFileName(name) is not None:
                    i = Image.open(os.path.join(root, name))
                    images.append([os.path.join(root, name), i.size[0], i.size[1]])
                    sizes.append(i.size[0])
        if len(images) > 0:
            targetWidth = max(set(sizes), key=sizes.count)
            for i in images:
                targetHeight += i[2]
                imagesValid.append(i[0])
            # Silently drop directories that contain too many images
            # 131072 = GIMP_MAX_IMAGE_SIZE / 4
            if targetHeight > 131072:
                return None
            result = Image.new('RGB', (targetWidth, targetHeight))
            y = 0
            for i in imagesValid:
                img = Image.open(i).convert('RGB')
                if img.size[0] < targetWidth or img.size[0] > targetWidth:
                    widthPercent = (targetWidth / float(img.size[0]))
                    heightSize = int((float(img.size[1]) * float(widthPercent)))
                    img = ImageOps.fit(img, (targetWidth, heightSize), method=Image.Resampling.BICUBIC,
                                       centering=(0.5, 0.5))
                result.paste(img, (0, y))
                y += img.size[1]
                os.remove(i)
            savePath = os.path.split(imagesValid[0])
            result.save(os.path.join(savePath[0], os.path.splitext(savePath[1])[0] + '.png'), 'PNG')
    except Exception:
        return str(sys.exc_info()[1]), sanitizeTrace(sys.exc_info()[2])


def detectSolid(img):
    return not ImageChops.invert(img).getbbox() or not img.getbbox()


def splitImageTick(output):
    if output:
        splitWorkerOutput.append(output)
        splitWorkerPool.terminate()
    if GUI:
        GUI.progressBarTick.emit('tick')
        if not GUI.conversionAlive:
            splitWorkerPool.terminate()


# noinspection PyUnboundLocalVariable
def splitImage(work):
    try:
        path = work[0]
        name = work[1]
        opt = work[2]
        filePath = os.path.join(path, name)
        Image.warnings.simplefilter('error', Image.DecompressionBombWarning)
        Image.MAX_IMAGE_PIXELS = 1000000000
        imgOrg = Image.open(filePath).convert('RGB')
        imgProcess = Image.open(filePath).convert('1')
        widthImg, heightImg = imgOrg.size
        if heightImg > opt.height:
            if opt.debug:
                drawImg = Image.open(filePath).convert(mode='RGBA')
                draw = ImageDraw.Draw(drawImg)

            # Find panels
            yWork = 0
            panelDetected = False
            panels = []
            while yWork < heightImg:
                tmpImg = imgProcess.crop([4, yWork, widthImg-4, yWork + 4])
                solid = detectSolid(tmpImg)
                if not solid and not panelDetected:
                    panelDetected = True
                    panelY1 = yWork - 2
                if heightImg - yWork <= 5:
                    if not solid and panelDetected:
                        panelY2 = heightImg
                        panelDetected = False
                        panels.append((panelY1, panelY2, panelY2 - panelY1))
                if solid and panelDetected:
                    panelDetected = False
                    panelY2 = yWork + 6
                    panels.append((panelY1, panelY2, panelY2 - panelY1))
                yWork += 5

            # Split too big panels
            panelsProcessed = []
            for panel in panels:
                if panel[2] <= opt.height * 1.5:
                    panelsProcessed.append(panel)
                elif panel[2] < opt.height * 2:
                    diff = panel[2] - opt.height
                    panelsProcessed.append((panel[0], panel[1] - diff, opt.height))
                    panelsProcessed.append((panel[1] - opt.height, panel[1], opt.height))
                else:
                    parts = round(panel[2] / opt.height)
                    diff = panel[2] // parts
                    for x in range(0, parts):
                        panelsProcessed.append((panel[0] + (x * diff), panel[1] - ((parts - x - 1) * diff), diff))

            if opt.debug:
                for panel in panelsProcessed:
                    draw.rectangle([(0, panel[0]), (widthImg, panel[1])], (0, 255, 0, 128), (0, 0, 255, 255))
                debugImage = Image.alpha_composite(imgOrg.convert(mode='RGBA'), drawImg)
                debugImage.save(os.path.join(path, os.path.splitext(name)[0] + '-debug.png'), 'PNG')

            # Create virtual pages
            pages = []
            currentPage = []
            pageLeft = opt.height
            panelNumber = 0
            for panel in panelsProcessed:
                if pageLeft - panel[2] > 0:
                    pageLeft -= panel[2]
                    currentPage.append(panelNumber)
                    panelNumber += 1
                else:
                    if len(currentPage) > 0:
                        pages.append(currentPage)
                    pageLeft = opt.height - panel[2]
                    currentPage = [panelNumber]
                    panelNumber += 1
            if len(currentPage) > 0:
                pages.append(currentPage)

            # Create pages
            pageNumber = 1
            for page in pages:
                pageHeight = 0
                targetHeight = 0
                for panel in page:
                    pageHeight += panelsProcessed[panel][2]
                if pageHeight > 15:
                    newPage = Image.new('RGB', (widthImg, pageHeight))
                    for panel in page:
                        panelImg = imgOrg.crop([0, panelsProcessed[panel][0], widthImg, panelsProcessed[panel][1]])
                        newPage.paste(panelImg, (0, targetHeight))
                        targetHeight += panelsProcessed[panel][2]
                    newPage.save(os.path.join(path, os.path.splitext(name)[0] + '-' + str(pageNumber) + '.png'), 'PNG')
                    pageNumber += 1
            os.remove(filePath)
    except Exception:
        return str(sys.exc_info()[1]), sanitizeTrace(sys.exc_info()[2])


def getOutputDirectory(sourceDir):
    if args.output:
        if args.inPlace:
            targetDir = os.path.abspath(args.output) + os.path.sep + os.path.basename(sourceDir)
        else:
            targetDir = os.path.abspath(args.output) + os.path.sep + os.path.basename(sourceDir) + "-Splitted"
    elif args.inPlace:
        targetDir = sourceDir
    else:
        targetDir = sourceDir + "-Splitted"
    if os.path.isdir(targetDir) and not args.inPlace:
        counter = 0
        while os.path.isdir(targetDir + str(counter)):
            counter += 1
        targetDir = targetDir + str(counter)
    return os.path.abspath(targetDir)


def main(argv=None, qtgui=None):
    global GUI, args, splitWorkerPool, splitWorkerOutput, mergeWorkerPool, mergeWorkerOutput
    parser = ArgumentParser(prog="kcc-c2p", usage="Usage: kcc-c2p [options] [input]", add_help=False)
    mainOptions = parser.add_argument_group("MANDATORY")
    otherOptions = parser.add_argument_group("OTHER")

    mainOptions.add_argument("input", action="extend", nargs="*", default=None,
                             help="Full path to comic folder(s) to be proccessed. Separate multiple inputs"
                             " with spaces.")
    mainOptions.add_argument("-y", "--height", type=int, dest="height", default="0",
                             help="Height of the target device screen")
    mainOptions.add_argument("-i", "--in-place", action="store_true", dest="inPlace", default=False,
                             help="Overwrite source directory")
    mainOptions.add_argument("-m", "--merge", action="store_true", dest="merge", default=False,
                             help="Combine every directory into a single image before splitting")

    otherOptions.add_argument("-l", "--log", action="store_true", dest="log",
                            help="Write logs to /kcc/logs/kcc-c2p.log")
    mainOptions.add_argument("-o", "--output", action="store", dest="output", default=None,
                             help="Output generated directories to specified directory")

    otherOptions.add_argument("-d", "--debug", action="store_true", dest="debug", default=False,
                              help="Create a debug file for every split image")
    otherOptions.add_argument("-h", "--help", action="help",
                              help="Show this help message and exit")
    args = parser.parse_args(argv)
    logname = "kcc-c2p"
    createLogger(logname, args)
    logger = logging.getLogger(logname)
    intro(logname)
    if qtgui:
        GUI = qtgui
    else:
        GUI = None
    if not argv or args.input == []:
        parser.print_help()
        return 1
    if args.height > 0:
        countinput = 1
        targetDirsList = []
        for sourceDir in args.input:
            sourceDir = os.path.abspath(sourceDir)
            if os.path.isdir(sourceDir):
                targetDir = getOutputDirectory(sourceDir)
                print("\nWorking on " + "(" + str(countinput) + "/" + str(len(args.input)) + ") - " +
                      os.path.normpath(sourceDir))
                workDir = getWorkFolder(sourceDir,"KCCP-", ebook=False)
                work = []
                pagenumber = 1
                splitWorkerOutput = []
                splitWorkerPool = Pool(maxtasksperchild=10)
                if args.merge:
                    logger.info("Merging images...")
                    directoryNumer = 1
                    mergeWork = []
                    mergeWorkerOutput = []
                    mergeWorkerPool = Pool(maxtasksperchild=10)
                    mergeWork.append([workDir])
                    for root, dirs, files in os.walk(workDir, False):
                        dirs, files = walkSort(dirs, files)
                        for directory in dirs:
                            directoryNumer += 1
                            mergeWork.append([os.path.join(root, directory)])
                    if GUI:
                        GUI.progressBarTick.emit('Combining images')
                        GUI.progressBarTick.emit(str(directoryNumer))
                    for i in mergeWork:
                        mergeWorkerPool.apply_async(func=mergeDirectory, args=(i, ), callback=mergeDirectoryTick)
                    mergeWorkerPool.close()
                    mergeWorkerPool.join()
                    if GUI and not GUI.conversionAlive:
                        rmtree(targetDir, True)
                        # raise UserWarning("Conversion interrupted.")
                        sys.exit(logger.exception("CRITICAL: Conversion interrupted."))
                if len(mergeWorkerOutput) > 0:
                        rmtree(workDir, True)
                        # raise RuntimeError("One of workers crashed. Cause: " + mergeWorkerOutput[0][0],
                                     #    mergeWorkerOutput[0][1])
                        sys.exit(logger.exception(mergeWorkerOutput[0][1] + "CRITICAL: One of workers crashed. Cause: " +
                                    mergeWorkerOutput[0][0]))
            logger.info("Splitting images...")
                for root, _, files in os.walk(workDir, False):
                    for name in files:
                        if getImageFileName(name) is not None:
                            pagenumber += 1
                            work.append([root, name, args])
                        else:
                            os.remove(os.path.join(root, name))
                if GUI:
                    GUI.progressBarTick.emit('Splitting images')
                    GUI.progressBarTick.emit(str(pagenumber))
                    GUI.progressBarTick.emit('tick')
                if len(work) > 0:
                    for i in work:
                        splitWorkerPool.apply_async(func=splitImage, args=(i, ), callback=splitImageTick)
                    splitWorkerPool.close()
                    splitWorkerPool.join()
                    if GUI and not GUI.conversionAlive:
                        rmtree(targetDir, True)
                        # raise UserWarning("Conversion interrupted.")
                        sys.exit(logger.exception("CRITICAL: Conversion interrupted."))
                if len(splitWorkerOutput) > 0:
                        rmtree(workDir, True)
                        # raise RuntimeError("One of workers crashed. Cause: " + splitWorkerOutput[0][0],
                     #                    splitWorkerOutput[0][1])
                    sys.exit(logger.exception(splitWorkerOutput[0][1] + "CRITICAL: One of workers crashed. Cause: " +
                                    splitWorkerOutput[0][0]))
                    if args.inPlace:
                        rmtree(targetDir)
                    copytree(workDir, targetDir)
                    rmtree(workDir)
                else:
                    rmtree(workDir, True)
                    # raise UserWarning("Source directory is empty.")
                countinput += 1
                targetDirsList.append(targetDir)
                    sys.exit(logger.exception("CRITICAL: Source directory is empty."))
        else:
                # raise UserWarning("Provided input is not a directory:" + sourceDir)
        print("\nThe following directories were successfully created:")
        for targetDir in targetDirsList:
            print(os.path.normpath(targetDir))
            sys.exit(logger.exception("CRITICAL: Provided path is not a directory."))
    else:
        # raise UserWarning("Target height is not set.")
        sys.exit(logger.exception("CRITICAL: Target height is not set."))
