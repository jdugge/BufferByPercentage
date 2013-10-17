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
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from bufferbypercentagedialog import BufferByPercentageDialog
import os.path

# Import the utilities from the fTools plugin (a standard QGIS plugin),
# which provide convenience functions for handling QGIS vector layers
import sys, os, imp
import fTools
path = os.path.dirname(fTools.__file__)
ftu = imp.load_source('ftools_utils', os.path.join(path,'tools','ftools_utils.py'))


class BufferByPercentage:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'bufferbypercentage_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = BufferByPercentageDialog()

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/bufferbypercentage/icon.png"),
            u"Buffer by percentage", self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Buffer by Percentage", self.action)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&Buffer by Percentage", self.action)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        # Populate the combo boxes
        self.dlg.populateLayers()
        
        self.dlg.show()
        result = self.dlg.exec_()
        if result == 1:
            self.target_factor = float(self.dlg.ui.param.text())/100.0
            self.segments = self.dlg.ui.segments.value()
            
            layer = ftu.getMapLayerByName(self.dlg.ui.inputLayer.currentText())
            fieldList = list(layer.dataProvider().fields())
            
            if self.dlg.ui.radioOutputLayer.isChecked():
                shapefilename = self.dlg.ui.outputLayer.text()
                if shapefilename == "":
                    return 1
            
            attributeIndex = -1    
            if self.dlg.ui.radioPercentageField.isChecked():
                attributeName = self.dlg.ui.dropdownPercentageField.currentText()
                attributeIndex = layer.dataProvider().fieldNameIndex(attributeName)
            
            nFeatures = layer.featureCount()
            
            
            # Create a memory layer for storing the results
            resultl = QgsVectorLayer("Polygon", "result", "memory")
            resultpr = resultl.dataProvider()
            resultpr.addAttributes(fieldList)
            
                
                
            
            featuresScaled = []
            # Loop over the features
            for i, feature in enumerate(layer.dataProvider().getFeatures()):
                self.iface.mainWindow().statusBar().showMessage("Buffering feature {} of {}".format(i+1,nFeatures))
                self.area_unscaled = feature.geometry().area()
                
                if attributeIndex >= 0:
                    if feature[attributeIndex] == "":
                        percentage = 0
                    else:
                        percentage = float(feature[attributeIndex])
                    
                    self.target_factor = max(0,percentage/100.0)
                    
                # Find target buffer length
                buffer_initial = 0.1*(feature.geometry().boundingBox().width() +
                                         feature.geometry().boundingBox().height() )
                
                
                buffer_length = self.secant(self.func,buffer_initial, 2*buffer_initial, feature)
            
                # Assign feature the buffered geometry
                feature.setGeometry(feature.geometry().buffer(buffer_length,self.segments))
                
                featuresScaled.append(feature)
            
            self.iface.mainWindow().statusBar().showMessage("Adding features to results layer")    
            resultpr.addFeatures(featuresScaled)
            
            if self.dlg.ui.radioMemoryLayer.isChecked():
                QgsMapLayerRegistry.instance().addMapLayer(resultl)
            elif self.dlg.ui.radioOutputLayer.isChecked():
                error = QgsVectorFileWriter.writeAsVectorFormat(resultl, shapefilename, "CP1250", None, "ESRI Shapefile")
                if self.dlg.ui.checkboxAddToCanvas.isChecked():
                    layername = os.path.splitext(os.path.basename(str(shapefilename)))[0]
                    vlayer = QgsVectorLayer(shapefilename, layername, "ogr")
                    QgsMapLayerRegistry.instance().addMapLayer(vlayer)
            self.iface.messageBar().pushMessage("Buffer by Percentage", "Process complete")
            
            self.iface.mainWindow().statusBar().clearMessage()
            self.iface.mapCanvas().refresh()
                    
    # Define the function for which to find the root
    def func(self, buffer_length, feature):
        geometry_scaled = feature.geometry().buffer(buffer_length,self.segments)
        area_scaled = geometry_scaled.area()
        return area_scaled/self.area_unscaled-(self.target_factor)
        
    # Secant method for iteratively finding the root of a function
    # Taken from http://www.physics.rutgers.edu/~masud/computing/WPark_recipes_in_python.html
    def secant(self, func, oldx, x, *args, **kwargs):
        TOL = kwargs.pop('TOL',1e-6) 
        oldf, f = func(oldx, *args), func(x, *args)
        if (abs(f) > abs(oldf)):
            oldx, x = x, oldx
            oldf, f = f, oldf
        while 1:
            dx = f * (x - oldx) / float(f - oldf)
            if abs(dx) < TOL * (1 + abs(x)): return x - dx
            oldx, x = x, x - dx
            oldf, f = f, func(x, *args)
