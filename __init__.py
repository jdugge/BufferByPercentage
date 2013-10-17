# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BufferByPercentage
                                 A QGIS plugin
 Buffer polygon features so the buffered area is a specified percentage of the original area
                             -------------------
        begin                : 2013-10-12
        copyright            : (C) 2013 by Juernjakob Dugge
        email                : juernjakob@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def name():
    return "Buffer by Percentage"


def description():
    return "Buffer polygon features so the buffered area is a specified percentage of the original area"


def version():
    return "Version 0.1"


def icon():
    return "icon.png"


def qgisMinimumVersion():
    return "2.0"

def author():
    return "Juernjakob Dugge"

def email():
    return "juernjakob@gmail.com"

def classFactory(iface):
    # load BufferByPercentage class from file BufferByPercentage
    from bufferbypercentage import BufferByPercentage
    return BufferByPercentage(iface)
