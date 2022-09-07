# KCC

[![GitHub release](https://img.shields.io/github/release/ciromattia/kcc.svg)](https://github.com/ciromattia/kcc/releases)
[![GitHub release](https://img.shields.io/github/v/release/darodi/kcc?display_name=tag&include_prereleases)](https://github.com/darodi/kcc/releases)
[![PyPI](https://img.shields.io/pypi/v/KindleComicConverter.svg)](https://pypi.python.org/pypi/KindleComicConverter)
[![AUR](https://img.shields.io/aur/version/kcc.svg)](https://aur.archlinux.org/packages/kcc/)

**Kindle Comic Converter** is a Python app to convert comic/manga files or folders to EPUB, Panel View MOBI or E-Ink optimized CBZ.
It was initially developed for Kindle but since version 4.6 it outputs valid EPUB 3.0 so _**despite its name, KCC is
actually a comic/manga to EPUB converter that every e-reader owner can happily use**_.
It can also optionally optimize images by applying a number of transformations.

### A word of warning
**KCC** _is not_ [Amazon's Kindle Comic Creator](http://www.amazon.com/gp/feature.html?ie=UTF8&docId=1001103761) nor is in any way endorsed by Amazon.
Amazon's tool is for comic publishers and involves a lot of manual effort, while **KCC** is for comic/manga readers.
_KC2_ in no way is a replacement for **KCC** so you can be quite confident we are going to carry on developing our little monster ;-)

### Issues / new features / donations
If you have general questions about usage, feedback etc. please [post it here](http://www.mobileread.com/forums/showthread.php?t=207461).
If you have some **technical** problems using KCC please [file an issue here](https://github.com/ciromattia/kcc/issues/new).
If you can fix an open issue, fork & make a pull request.

If you find **KCC** valuable you can consider donating to the authors:
- Ciro Mattia Gonano:
  - [![Donate PayPal](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=D8WNYNPBGDAS2)
  - [![Donate Flattr](https://img.shields.io/badge/Donate-Flattr-green.svg)](http://flattr.com/thing/2260449/ciromattiakcc-on-GitHub)
- Paweł Jastrzębski:
  - [![Donate PayPal](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=YTTJ4LK2JDHPS)
  - [![Donate Bitcoin](https://img.shields.io/badge/Donate-Bitcoin-green.svg)](https://jastrzeb.ski/donate/)

## BINARY RELEASES
You can find the latest beta binaries here:
**https://github.com/darodi/kcc/releases**


You can find the latest released binary at the following links:
- **[Windows](http://kcc.iosphe.re/Windows/) (64-bit only)**
- **[macOS](http://kcc.iosphe.re/OSX/) (10.14+)**
- **Linux:** Currently unavailable.

## PYPI
**KCC** is also available on PyPI.
```
pip install --user KindleComicConverter
```

## DEPENDENCIES
Following software is required to run Linux version of **KCC** and/or bare sources:
- Python 3.3+
- [PyQt5](https://pypi.python.org/pypi/PyQt5) 5.6.0+ (only needed for GUI)
- [Pillow](https://pypi.python.org/pypi/Pillow) 4.0.0+ (5.2.0+ needed for WebP support)
- [psutil](https://pypi.python.org/pypi/psutil) 5.0.0+
- [python-slugify](https://pypi.python.org/pypi/python-slugify) 1.2.1+, <3.0.0
- [raven](https://pypi.python.org/pypi/raven) 6.0.0+ (only needed for GUI)
- [mozjpeg](https://pypi.org/project/mozjpeg-lossless-optimization)
- [pandas](https://pypi.org/project/pandas)
- [rich](https://pypi.org/project/rich) (Only needed for fancy text and progress bars. Else use noformat option)
On Debian based distributions these two commands should install all needed dependencies:
```
sudo apt-get install python3 python3-dev python3-pip libpng-dev libjpeg-dev p7zip-full
pip3 install --user --upgrade pillow python-slugify psutil pyqt5 raven mozjpeg-lossless-optimization pandas rich
```

### Optional dependencies
- [KindleGen](http://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000765211) v2.9+ in a directory reachable by your _PATH_ or in _KCC_ directory *(For MOBI generation)*
- [7z](http://www.7-zip.org/download.html) *(For CBZ/ZIP, CBR/RAR, 7z/CB7 support)*

## INPUT FORMATS
**KCC** can understand and convert, at the moment, the following input types:
- Folders containing: PNG, JPG, GIF or WebP files
- CBZ, ZIP *(With `7z` executable)*
- CBR, RAR *(With `7z` executable)*
- CB7, 7Z *(With `7z` executable)*
- PDF *(Only extracting JPG images)*

## USAGE

Should be pretty self-explanatory. All options have detailed information in tooltips.
After completed conversion, you should find ready file alongside the original input file (same directory).

Please check [our wiki](https://github.com/ciromattia/kcc/wiki/) for more details.
Updated [profile](https://github.com/rourien/kcc/wiki/Profiles) list and instructions for adding a custom profile.

CLI version of **KCC** is intended for power users. It allows using options that might not be compatible and decrease the quality of output.

### Standalone `kcc-c2e.py` usage:

```
Usage: kcc-c2e [options] [input]

MANDATORY:
  input                 Full path to comic folder(s) or file(s) to be proccessed. Separate multiple
                        inputs with spaces.

MAIN:
  -p PROFILE, --profile PROFILE
                        Device profile (Common options: K578, KPW5, KV, KoGHD, KoA, KoAHD, KoAH2O, KoAO, KoC, KoL,
                        KoF, KoN, KoE, KoS). For a list of all avaliable profiles, type -h profile [Default=KV]
  -m, --manga-style     Manga style (right-to-left reading and splitting)
  -q, --hq              Try to increase the quality of magnification
  -2, --two-panel       Display two not four panels in Panel View mode
  -w, --webtoon         Webtoon processing mode

PROCESSING:
  -n, --noprocessing    Do not modify image and ignore any profile or processing option
  -u, --upscale         Resize images smaller than device's resolution
  -s, --stretch         Stretch images to device's resolution
  -r {0,1,2}, --splitter {0,1,2}
                        Double page parsing mode. 0: Split 1: Rotate 2: Both [Default=0]
  -g GAMMA, --gamma GAMMA
                        Apply gamma correction to linearize the image [Default=Auto]
  -c {0,1,2}, --cropping {0,1,2}
                        Set cropping mode. 0: Disabled 1: Margins 2: Margins + page numbers
                        [Default=2]
  --cp CROPPINGPOWER, --croppingpower CROPPINGPOWER
                        Set cropping power [Default=1.0]
  --cM CROPPINGMINIMUM, --croppingminimum CROPPINGMINIMUM
                        Set cropping minimum area ratio [Default=0.0]
  --bb, --blackborders  Disable autodetection and force black borders
  --wb, --whiteborders  Disable autodetection and force white borders
  --fc, --forcecolor    Don't convert images to grayscale
  --fp, --forcepng      Create PNG files instead JPEG
  --mj, --mozjpeg       Create JPEG files using mozJpeg

OUTPUT SETTINGS:
  -o OUTPUT, --output OUTPUT
                        Output generated file to specified directory or file
  --cst COPYSOURCETREE, --copysourcetree COPYSOURCETREE
                        Additional option for use with --output. Name of the top most directory to be
                        used when recreating the source directory tree in the output directory.
  -t TITLE, --title TITLE
                        Comic title [Default=filename or directory name]
  -f {Auto,MOBI,EPUB,CBZ,KFX}, --format {Auto,MOBI,EPUB,CBZ,KFX}
                        Output format (Available options: Auto, MOBI, EPUB, CBZ, KFX) [Default=Auto]
  -b {0,1,2}, --batchsplit {0,1,2}
                        Split output into multiple files. 0: Don't split 1: Automatic mode 2:
                        Consider every subdirectory as separate volume [Default=0]
  -e {0,1,2,3,4,5}, --skipexisting {0,1,2,3,4,5}
                        Skip processing specific files. 0: Do not skip. 1: Skip if the wanted file
                        already exists in the output directory. 2: Skip if the source file was already
                        processed. 3: Copy the already processed file to the output directory. 4: Use
                        both options 1 and 2. 5: Use both options 1 and 3. [Default=0]
  -z PADZEROS, --padzeros PADZEROS
                        Pad "_kcc(#)" with given number of zeros. [Default=0]
  --cci, --copycomicinfo
                        Copy ComicInfo.xml to generated file

CUSTOM PROFILE:
  --cw CUSTOMWIDTH, --customwidth CUSTOMWIDTH
                        Replace screen width provided by device profile
  --ch CUSTOMHEIGHT, --customheight CUSTOMHEIGHT
                        Replace screen height provided by device profile

OTHER:
  -h, --help            Show this help message and exit
```

### Standalone `kcc-c2p.py` usage:

```
Usage: kcc-c2p [options] [input]

MANDATORY:
  input                 Full path to comic folder to be proccessed
  -y HEIGHT, --height HEIGHT
                        Height of the target device screen
  -i, --in-place        Overwrite source directory
  -m, --merge           Combine every directory into a single image before splitting

OTHER:
  -d, --debug           Create debug file for every split image
  -h, --help            Show this help message and exit
```

## CREDITS
**KCC** is made by [Ciro Mattia Gonano](http://github.com/ciromattia) and [Paweł Jastrzębski](http://github.com/AcidWeb).

This script born as a cross-platform alternative to `KindleComicParser` by **Dc5e** (published [here](http://www.mobileread.com/forums/showthread.php?t=192783)).

The app relies and includes the following scripts:

 - `DualMetaFix` script by **K. Hendricks**. Released with GPL-3 License.
 - `image.py` class from **Alex Yatskov**'s [Mangle](https://github.com/FooSoft/mangle/) with subsequent [proDOOMman](https://github.com/proDOOMman/Mangle)'s and [Birua](https://github.com/Birua/Mangle)'s patches.
 - `df_to_table` function from **Avi Perl**'s [Rich Tools](https://github.com/avi-perl/rich_tools)
 - Icon is by **Nikolay Verin** ([http://ncrow.deviantart.com/](http://ncrow.deviantart.com/)) and released under [CC BY-NC-SA 3.0](http://creativecommons.org/licenses/by-nc-sa/3.0/) License.

## SAMPLE FILES CREATED BY KCC
* [Kindle Oasis 2 / 3](http://kcc.iosphe.re/Samples/Ubunchu!-KO.mobi)
* [Kindle Paperwhite 3 / 4 / Voyage / Oasis](http://kcc.iosphe.re/Samples/Ubunchu!-KV.mobi)
* [Kindle Paperwhite 1 / 2](http://kcc.iosphe.re/Samples/Ubunchu!-KPW.mobi)
* [Kindle](http://kcc.iosphe.re/Samples/Ubunchu!-K578.mobi)
* [Kobo Aura](http://kcc.iosphe.re/Samples/Ubunchu-KoA.kepub.epub)
* [Kobo Aura HD](http://kcc.iosphe.re/Samples/Ubunchu-KoAHD.kepub.epub)
* [Kobo Aura H2O](http://kcc.iosphe.re/Samples/Ubunchu-KoAH2O.kepub.epub)
* [Kobo Aura ONE](http://kcc.iosphe.re/Samples/Ubunchu-KoAO.kepub.epub)
* [Kobo Forma](http://kcc.iosphe.re/Samples/Ubunchu-KoF.kepub.epub)

## PRIVACY
**KCC** is initiating internet connections in two cases:
* During startup - Version check.
* When error occurs - Automatic reporting on Windows and macOS.

## KNOWN ISSUES
Please check [wiki page](https://github.com/ciromattia/kcc/wiki/Known-issues).

## COPYRIGHT
Copyright (c) 2012-2019 Ciro Mattia Gonano and Paweł Jastrzębski.
**KCC** is released under ISC LICENSE; see LICENSE.txt for further details.
