"""
autoLoadUI.py
    *Auto Load UI*
-loadUI(): Emulates the PyQt5.uic.loadUi() function
-autoLoadUI(): automatically loads the UI file that has the same name as class file (i.e. "mainwindow.py" -> "mainwindow.ui")
    Simply call "autoLoadUI(self)" in the class definition after the "super()" call.
Author: Danny Yoon
Version: 1.0.0

"""

# Modifications by Danny Yoon <twoyoon@gmail.com>
# Change list:
# - 1.0.0 (2021-11-22):
#   - auto loads <file>.ui where <file> is the base name of the calling file.
#   - updated to work with pyside2
#   - added support for custom widgets defined in .ui file, like the way PyQt5 uic does it.
#       The header file for the custom widget is the package name. (without the '.py' or '.h' extension)
#   - Instead of passing a dict of custom widgets, you can pass a list of classes.

# Modifications by Charl Botha <cpbotha@vxlabs.com>
# https://gist.github.com/cpbotha/1b42a20c8f3eb9bb7cb8
# * customWidgets support (registerCustomWidget() causes segfault in
#   pyside 1.1.2 on Ubuntu 12.04 x86_64)
# * workingDirectory support in loadUi

# Copyright (c) 2011 Sebastian Wiesner <lunaryorn@gmail.com>
# Original code was here but is now missing:
# https://github.com/lunaryorn/snippets/blob/master/qt4/designer/pyside_dynamic.py
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import os
import sys

from PySide2.QtCore import Slot, QMetaObject
from PySide2.QtUiTools import QUiLoader


class _UiLoader(QUiLoader):
    """
    Subclass :class:`~PySide.QtUiTools.QUiLoader` to create the user interface
    in a base instance.
    Unlike :class:`~PySide.QtUiTools.QUiLoader` itself this class does not
    create a new instance of the top-level widget, but creates the user
    interface in an existing instance of the top-level class.
    This mimics the behaviour of :func:`PyQt4.uic.loadUi`.
    """

    def __init__(self, baseinstance, customWidgets=None):
        """
        Create a loader for the given ``baseinstance``.
        The user interface is created in ``baseinstance``, which must be an
        instance of the top-level class in the user interface to load, or a
        subclass thereof.
        ``customWidgets`` is a dictionary mapping from class name to class object
        for widgets that you've promoted in the Qt Designer interface. Usually,
        this should be done by calling registerCustomWidget on the QUiLoader, but
        with PySide 1.1.2 on Ubuntu 12.04 x86_64 this causes a segfault.
        ``parent`` is the parent object of this loader.
        """

        QUiLoader.__init__(self, baseinstance)
        self.baseinstance = baseinstance
        self.customWidgets = customWidgets


    def createWidget(self, class_name, parent=None, name=''):
        """
        Function that is called for each widget defined in ui file,
        overridden here to populate baseinstance instead.
        """

        if parent is None and self.baseinstance:
            # supposed to create the top-level widget, return the base instance
            # instead
            return self.baseinstance

        else:
            if class_name in self.availableWidgets():
                # create a new widget for child widgets
                widget = QUiLoader.createWidget(self, class_name, parent, name)

            else:
                # if not in the list of availableWidgets, must be a custom widget
                # this will raise KeyError if the user has not supplied the
                # relevant class_name in the dictionary, or TypeError, if
                # customWidgets is None
                try:
                    # widget = self.customWidgets[class_name](parent)
                    widget = self.customWidgets[class_name](parent)

                except (TypeError, KeyError) as e:
                    raise Exception('No custom widget ' + class_name + ' found in customWidgets param of __UiLoader __init__.')

            if self.baseinstance:
                # set an attribute for the new child widget on the base
                # instance, just like PyQt5.uic.loadUi does.
                setattr(self.baseinstance, name, widget)

                # this outputs the various widget names, e.g.
                # sampleGraphicsView, dockWidget, samplesTableView etc.
                #print(name)

            return widget


def autoloadUi(baseinstance=None, customWidgets=None):
    """
    Dynamically load a user interface.  Detects the file name that's calling this
    function and looks for "<file>.ui".

    USAGE: put this in __init__ after the calling the super class like below:
    class MyClass(QWidget):
        def __init__(self, parent=None):    # Don't forget to pass the parent to the superclass!
            super(MyClass, self).__init__(parent)
            autoloadUi(self)   # <--- Call autoloadeUi() here

    NOTE: The base class of your class should equal the base class of .ui file

    If ``baseinstance`` is ``None``, the a new instance of the top-level widget
    will be created.  Otherwise, the user interface is created within the given
    ``baseinstance``.  In this case ``baseinstance`` must be an instance of the
    top-level widget class in the UI file to load, or a subclass thereof.  In
    other words, if you've created a ``QMainWindow`` interface in the designer,
    ``baseinstance`` must be a ``QMainWindow`` or a subclass thereof, too.  You
    cannot load a ``QMainWindow`` UI file with a plain
    :class:`~PySide.QtGui.QWidget` as ``baseinstance``.
    ``customWidgets`` is a list of classes
    for widgets that you've promoted in the Qt Designer interface. Usually,
    this should be done by calling registerCustomWidget on the QUiLoader, but
    with PySide 1.1.2 on Ubuntu 12.04 x86_64 this causes a segfault.
    :method:`~PySide.QtCore.QMetaObject.connectSlotsByName()` is called on the
    created user interface, so you can implemented your slots according to its
    conventions in your widget class.
    Return ``baseinstance``, if ``baseinstance`` is not ``None``.  Otherwise
    return the newly created instance of the user interface.
    """

    # Find the filename that called this function
    namespace = sys._getframe(1).f_globals  # caller's globals
    filepath= namespace['__file__']
    basepath = os.path.splitext(filepath)[0]
    dirpath = os.path.dirname(basepath)
    uifile = basepath + '.ui'

    # Get the string names of the custom classes.
    customWidgetDict = {}
    if customWidgets:
        for widget in customWidgets:
            customWidgetDict[widget.__name__] = widget
    loader = _UiLoader(baseinstance, customWidgetDict)

    # Set the working directory! Otherwise you'll see missing icons and pixmaps because paths are calculated wrong.
    loader.setWorkingDirectory(dirpath)

    # In the .ui file, find the custom class and header files and register them with the loader
    import xml.etree.ElementTree as ET
    tree = ET.parse(uifile)
    root = tree.getroot()
    customwidgets = root.find('customwidgets')
    if customwidgets is not None:
        widgets = customwidgets.findall('customwidget')
        if widgets:
            for w in widgets:
                classname = w.find('class').text
                header = w.find('header').text
                mod = __import__(header, fromlist=[classname])
                cls = getattr(mod, classname)
                loader.registerCustomWidget(cls)

    # Load the UI
    widget = loader.load(uifile)
    QMetaObject.connectSlotsByName(widget)
    return widget

def loadUi(uifile, baseinstance=None, customWidgets=None,
           workingDirectory=None):
    """
    Dynamically load a user interface from the given ``uifile``.
    ``uifile`` is a string containing a file name of the UI file to load.
    If ``baseinstance`` is ``None``, the a new instance of the top-level widget
    will be created.  Otherwise, the user interface is created within the given
    ``baseinstance``.  In this case ``baseinstance`` must be an instance of the
    top-level widget class in the UI file to load, or a subclass thereof.  In
    other words, if you've created a ``QMainWindow`` interface in the designer,
    ``baseinstance`` must be a ``QMainWindow`` or a subclass thereof, too.  You
    cannot load a ``QMainWindow`` UI file with a plain
    :class:`~PySide.QtGui.QWidget` as ``baseinstance``.
    ``customWidgets`` is a list of classes
    for widgets that you've promoted in the Qt Designer interface. Usually,
    this should be done by calling registerCustomWidget on the QUiLoader, but
    with PySide 1.1.2 on Ubuntu 12.04 x86_64 this causes a segfault.
    :method:`~PySide.QtCore.QMetaObject.connectSlotsByName()` is called on the
    created user interface, so you can implemented your slots according to its
    conventions in your widget class.
    Return ``baseinstance``, if ``baseinstance`` is not ``None``.  Otherwise
    return the newly created instance of the user interface.
    """

    # Get the string names of the custom classes.
    customWidgetDict = {}
    if customWidgets:
        for widget in customWidgets:
            customWidgetDict[widget.__name__] = widget

    loader = _UiLoader(baseinstance, customWidgetDict)

    if workingDirectory is not None:
        loader.setWorkingDirectory(workingDirectory)

    widget = loader.load(uifile)
    QMetaObject.connectSlotsByName(widget)
    return widget