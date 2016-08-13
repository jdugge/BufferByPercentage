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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

# Initialize Qt resources from file resources.py
from . import resources_rc  # lint:ok

# Import the code for the dialog
from .bufferbypercentagedialog import BufferByPercentageDialog

# Import the Processing libraries so we can add the algorithm to
# the Processing menu
from processing.core.Processing import Processing
from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterNumber
from processing.core.parameters import ParameterTableField
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector
from processing.core.AlgorithmProvider import AlgorithmProvider

import os.path

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
    TOL = kwargs.pop('TOL', 1e-6)
    oldf, f = func(oldx, *args), func(x, *args)
    if (abs(f) > abs(oldf)):
        oldx, x = x, oldx
        oldf, f = f, oldf
    while 1:
        dx = f * (x - oldx) / float(f - oldf)
        if abs(dx) < TOL * (1 + abs(x)):
            return x - dx
        oldx, x = x, x - dx
        oldf, f = f, func(x, *args)


# The "classic" plugin that appears in the "Plugins" menu.
# Also loads the Processing plugin.
class BufferByPercentagePlugin:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n',
            'bufferbypercentage_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = BufferByPercentageDialog()
        self.provider = BufferByPercentageProvider()

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/bufferbypercentage/icon.svg"),
            "Buffer by percentage", self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("&Buffer by Percentage", self.action)
        Processing.addProvider(self.provider, updateList=True)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu("&Buffer by Percentage", self.action)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        # Populate the combo boxes
        self.dlg.populateLayers()

        self.dlg.show()
        result = self.dlg.exec_()
        if result == 1:
            self.target_factor = float(self.dlg.ui.param.text()) / 100.0
            self.segments = self.dlg.ui.segments.value()

            layer = self.dlg.ui.inputLayer.itemData(
                self.dlg.ui.inputLayer.currentIndex()
            )
            fieldList = list(layer.dataProvider().fields())

            if self.dlg.ui.radioOutputLayer.isChecked():
                shapefilename = self.dlg.ui.outputLayer.text()
                if shapefilename == "":
                    return 1

            attributeIndex = -1
            if self.dlg.ui.radioPercentageField.isChecked():
                attributeName = self.dlg.ui.dropdownPercentageField\
                  .currentText()
                attributeIndex = layer.dataProvider()\
                  .fieldNameIndex(attributeName)

            nFeatures = layer.featureCount()

            # Create a memory layer for storing the results
            crsString = layer.crs().authid()
            resultl = QgsVectorLayer("Polygon?crs=" + crsString,
                "result", "memory")
            resultpr = resultl.dataProvider()
            resultpr.addAttributes(fieldList)

            featuresScaled = []
            # Loop over the features
            for i, feature in enumerate(layer.dataProvider().getFeatures()):
                self.iface.mainWindow().statusBar().showMessage(
                    "Buffering feature {} of {}".format(i + 1, nFeatures))

                if attributeIndex >= 0:
                    if feature[attributeIndex] == "":
                        percentage = 0
                    else:
                        percentage = float(feature[attributeIndex])

                    self.target_factor = max(0, percentage / 100.0)

                buffer_length = find_buffer_length(feature.geometry(),
                    self.target_factor, self.segments)

                # Assign feature the buffered geometry
                feature.setGeometry(feature.geometry().buffer(buffer_length,
                    self.segments))

                featuresScaled.append(feature)

            self.iface.mainWindow().statusBar()\
            .showMessage("Adding features to results layer")
            resultpr.addFeatures(featuresScaled)
            resultl.updateFields()

            if self.dlg.ui.radioMemoryLayer.isChecked():
                QgsMapLayerRegistry.instance().addMapLayer(resultl)
            elif self.dlg.ui.radioOutputLayer.isChecked():
                QgsVectorFileWriter.writeAsVectorFormat(resultl,
                    shapefilename, "CP1250", None, "ESRI Shapefile")
                if self.dlg.ui.checkboxAddToCanvas.isChecked():
                    layername = os.path.splitext(
                        os.path.basename(str(shapefilename)))[0]
                    vlayer = QgsVectorLayer(shapefilename, layername, "ogr")
                    QgsMapLayerRegistry.instance().addMapLayer(vlayer)
            self.iface.messageBar().pushMessage(
                "Buffer by Percentage", "Process complete", duration=3)

            self.iface.mainWindow().statusBar().clearMessage()
            self.iface.mapCanvas().refresh()


#Classes for the Processing plugin

class BufferByPercentageProvider(AlgorithmProvider):
    def __init__(self):
        AlgorithmProvider.__init__(self)

        self.alglist = [BufferByFixedPercentageAlgorithm(),
            BufferByVariablePercentageAlgorithm()]
        for alg in self.alglist:
            alg.provider = self

    def unload(self):
        AlgorithmProvider.unload(self)

    def getName(self):
        return 'Buffer by percentage'

    def getDescription(self):
        return 'Buffer by percentage'

    def getIcon(self):
        return QIcon(":/plugins/bufferbypercentage/icon.svg")

    def _loadAlgorithms(self):
        self.algs = self.alglist


class BufferByFixedPercentageAlgorithm(GeoAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    PERCENTAGE = 'PERCENTAGE'
    SEGMENTS = 'SEGMENTS'

    def defineCharacteristics(self):
        self.name = 'Fixed percentage buffer'
        self.group = 'Buffer by percentage'

        self.addParameter(ParameterVector(self.INPUT, 'Input layer',
                          [ParameterVector.VECTOR_TYPE_POLYGON], False))
        self.addParameter(ParameterNumber(self.PERCENTAGE, 'Percentage',
                          default=100.0))
        self.addParameter(ParameterNumber(self.SEGMENTS, 'Segments', 1,
                          default=5))
        self.addOutput(OutputVector(self.OUTPUT,
                       'Output layer with selected features'))

    def processAlgorithm(self, progress):
        layer = dataobjects.getObjectFromUri(
                self.getParameterValue(self.INPUT))
        percentage = float(self.getParameterValue(self.PERCENTAGE))
        segments = int(self.getParameterValue(self.SEGMENTS))

        writer = self.getOutputFromName(
                self.OUTPUT).getVectorWriter(layer.pendingFields().toList(),
                                             QGis.WKBPolygon, layer.crs())

        current = 0
        features = vector.features(layer)
        total = 100.0 / float(len(features))

        outFeat = QgsFeature()

        for inFeat in features:
            attrs = inFeat.attributes()
            inGeom = QgsGeometry(inFeat.geometry())
            buffer_length = find_buffer_length(inGeom,
                    percentage / 100.0, segments)
            outGeom = inGeom.buffer(buffer_length, segments)
            outFeat.setGeometry(outGeom)
            outFeat.setAttributes(attrs)
            writer.addFeature(outFeat)
            current += 1
            progress.setPercentage(int(current * total))

        del writer


class BufferByVariablePercentageAlgorithm(GeoAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    FIELD = 'FIELD'
    SEGMENTS = 'SEGMENTS'

    def defineCharacteristics(self):
        self.name = 'Variable percentage buffer'
        self.group = 'Buffer by percentage'

        self.addParameter(ParameterVector(self.INPUT, 'Input layer',
                          [ParameterVector.VECTOR_TYPE_POLYGON], False))
        self.addParameter(ParameterTableField(self.FIELD, 'Percentage field',
                          self.INPUT))
        self.addParameter(ParameterNumber(self.SEGMENTS, 'Segments', 1,
                          default=5))
        self.addOutput(OutputVector(self.OUTPUT,
                       'Output layer with selected features'))

    def processAlgorithm(self, progress):
        layer = dataobjects.getObjectFromUri(
                self.getParameterValue(self.INPUT))
        field = layer.fieldNameIndex(self.getParameterValue(self.FIELD))
        segments = int(self.getParameterValue(self.SEGMENTS))

        writer = self.getOutputFromName(
                self.OUTPUT).getVectorWriter(layer.pendingFields().toList(),
                                             QGis.WKBPolygon, layer.crs())

        current = 0
        features = vector.features(layer)
        total = 100.0 / float(len(features))

        outFeat = QgsFeature()

        for inFeat in features:
            attrs = inFeat.attributes()
            inGeom = QgsGeometry(inFeat.geometry())
            percentage = attrs[field]
            buffer_length = find_buffer_length(inGeom,
                    percentage / 100.0, segments)
            outGeom = inGeom.buffer(buffer_length, segments)
            outFeat.setGeometry(outGeom)
            outFeat.setAttributes(attrs)
            writer.addFeature(outFeat)
            current += 1
            progress.setPercentage(int(current * total))

        del writer
