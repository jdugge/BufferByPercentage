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


def classFactory(iface):
    # load BufferByPercentage class from file BufferByPercentage
    from .bufferbypercentage import BufferByPercentagePlugin, BufferByFixedPercentage
    return BufferByPercentagePlugin(iface)
