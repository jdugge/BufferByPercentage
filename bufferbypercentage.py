# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BufferByPercentage
                                 A QGIS plugin
 Buffer polygon features so the buffered area is a specified percentage of
 the original area
                              -------------------
        begin                : 2013-10-12
        copyright            : (C) 2016 by Juernjakob Dugge
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
"""
# Import the PyQt and QGIS libraries
# from PyQt5.QtCore import *
# from PyQt5.QtGui import QIcon

# from qgis.core import *

# Initialize Qt resources from file resources.py
# from . import resources_rc  # lint:ok

# Import the code for the dialog
# from .bufferbypercentagedialog import BufferByPercentageDialog

# Import the Processing libraries so we can add the algorithm to
# the Processing menu
from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from qgis.core import (
    QgsProcessingProvider,
    QgsApplication,
    QgsProcessing,
    QgsProcessingParameterNumber,
    QgsProcessingParameterField,
    QgsWkbTypes
)
from qgis.PyQt.QtGui import QIcon

from processing.algs.qgis.QgisAlgorithm import QgisFeatureBasedAlgorithm

import os

pluginPath = os.path.split(os.path.dirname(__file__))[0]


# from processing.core.Processing import Processing
# from processing.core.GeoAlgorithm import GeoAlgorithm
# from processing.core.parameters import ParameterVector
# from processing.core.parameters import ParameterNumber
# from processing.core.parameters import ParameterTableField
# from processing.core.outputs import OutputVector
# from processing.tools import dataobjects, vector
# from processing.core.AlgorithmProvider import AlgorithmProvider
# import processing
#
# import os.path
#
def find_buffer_length(geometry, target_factor, segments):
    """Find the buffer length that scales a geometry by a certain factor."""
    area_unscaled = geometry.area()
    buffer_initial = 0.1 * (geometry.boundingBox().width() +
                            geometry.boundingBox().height())

    buffer_length = secant(calculateError, buffer_initial,
                           2 * buffer_initial, geometry, segments,
                           area_unscaled, target_factor)

    return buffer_length


def calculateError(buffer_length, geometry, segments, area_unscaled,
                   target_factor):
    """Calculate the difference between the current and the target factor."""
    geometry_scaled = geometry.buffer(buffer_length, segments)
    area_scaled = geometry_scaled.area()

    return area_scaled / area_unscaled - target_factor


# Secant method for iteratively finding the root of a function
# Taken from
# http://www.physics.rutgers.edu/~masud/computing/WPark_recipes_in_python.html
def secant(func, oldx, x, *args, **kwargs):
    """Find the root of a function"""
    tolerance = kwargs.pop('tolerance', 1e-6)
    max_steps = kwargs.pop('max_steps', 100)

    steps = 0
    oldf, f = func(oldx, *args), func(x, *args)

    if (abs(f) > abs(oldf)):  # Determine the initial search direction
        oldx, x = x, oldx
        oldf, f = f, oldf

    while (f - oldf) != 0 and steps < max_steps:
        dx = f * (x - oldx) / float(f - oldf)

        if abs(dx) < tolerance * (1 + abs(x)):  # Converged
            return x - dx

        oldx, x = x, x - dx
        oldf, f = f, func(x, *args)
        while f <= 0:
            # Buffer length resulted in flipped polygon, reduce step size
            x = oldx  # Undo current step
            f = oldf
            dx *= 0.5  # Halve the step size
            oldx, x = x, x - dx
            oldf, f = f, func(x, *args)

        steps += 1

    # Did not converge
    return x - dx


class BufferByPercentagePlugin:
    def __init__(self, iface):
        self.provider = BufferByPercentageProvider()

    def initGui(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)


class BufferByPercentageProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()
        self.alglist = [
            BufferByFixedPercentage(),
            BufferByVariablePercentage()
        ]

    def getAlgs(self):
        return self.alglist

    def id(self, *args, **kwargs):
        return 'bufferbypercentage'

    def name(self, *args, **kwargs):
        return 'Buffer by Percentage'

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'bufferbypercentage', 'icon.svg'))

    def svgIconPath(self):
        return os.path.join(pluginPath, 'bufferbypercentage', 'icon.svg')

    def loadAlgorithms(self, *args, **kwargs):
        for alg in self.alglist:
            self.addAlgorithm(alg)


class BufferByFixedPercentage(QgisFeatureBasedAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    PERCENTAGE = 'PERCENTAGE'
    SEGMENTS = 'SEGMENTS'

    def __init__(self):
        super().__init__()
        self.percentage = None
        self.segments = None

    def name(self):
        return 'bufferbyfixedpercentage'

    def displayName(self, *args, **kwargs):
        return 'Buffer by Fixed Percentage'

    def group(self):
        return self.tr('Buffer by Percentage')

    def inputLayerTypes(self):
        return [QgsProcessing.TypeVectorPolygon]

    def outputName(self):
        return self.tr('Buffer')

    def outputType(self):
        return QgsProcessing.TypeVectorPolygon

    def outputWkbType(self, input_wkb_type):
        return QgsWkbTypes.Polygon

    def initParameters(self, config=None):
        self.addParameter(QgsProcessingParameterNumber(self.PERCENTAGE,
                                                       self.tr('Percentage'),
                                                       type=QgsProcessingParameterNumber.Double,
                                                       defaultValue=100.0))
        self.addParameter(QgsProcessingParameterNumber(self.SEGMENTS,
                                                       self.tr('Segments'),
                                                       type=QgsProcessingParameterNumber.Integer,
                                                       minValue=1,
                                                       defaultValue=5))

    def prepareAlgorithm(self, parameters, context, feedback):
        self.percentage = self.parameterAsDouble(parameters, self.PERCENTAGE,
                                                 context)
        self.segments = self.parameterAsInt(parameters, self.SEGMENTS, context)

        return True

    def processFeature(self, feature, context, feedback):
        input_geometry = feature.geometry()
        if input_geometry:
            buffer_length = find_buffer_length(input_geometry,
                                               self.percentage / 100.0,
                                               self.segments)

            output_geometry = input_geometry.buffer(buffer_length,
                                                    self.segments)

            feature.setGeometry(output_geometry)

        return feature


class BufferByVariablePercentage(QgisFeatureBasedAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    FIELD = 'FIELD'
    SEGMENTS = 'SEGMENTS'

    def __init__(self):
        super().__init__()
        self.percentage = None
        self.segments = None

    def name(self):
        return 'bufferbyvariablepercentage'

    def displayName(self, *args, **kwargs):
        return 'Buffer by Variable Percentage'

    def group(self):
        return self.tr('Buffer by Percentage')

    def inputLayerTypes(self):
        return [QgsProcessing.TypeVectorPolygon]

    def outputName(self):
        return self.tr('Buffer')

    def outputType(self):
        return QgsProcessing.TypeVectorPolygon

    def outputWkbType(self, input_wkb_type):
        return QgsWkbTypes.Polygon

    def initParameters(self, config=None):
        self.addParameter(QgsProcessingParameterField(self.FIELD,
                                                      self.tr(
                                                          'Percentage field'),
                                                      parentLayerParameterName=self.INPUT))
        self.addParameter(QgsProcessingParameterNumber(self.SEGMENTS,
                                                       self.tr('Segments'),
                                                       type=QgsProcessingParameterNumber.Integer,
                                                       minValue=1,
                                                       defaultValue=5))

    def prepareAlgorithm(self, parameters, context, feedback):
        self.field = self.parameterAsString(parameters,
                                                 self.FIELD, context)
        self.segments = self.parameterAsInt(parameters, self.SEGMENTS,
                                            context)

        return True

    def processFeature(self, feature, context, feedback):
        input_geometry = feature.geometry()
        percentage = feature[self.field]
        if input_geometry:
            buffer_length = find_buffer_length(input_geometry,
                                               percentage / 100.0,
                                               self.segments)

            output_geometry = input_geometry.buffer(buffer_length,
                                                    self.segments)

            feature.setGeometry(output_geometry)

        return feature
