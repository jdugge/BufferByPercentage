# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BufferByPercentageDialog
                                 A QGIS plugin
 Buffer polygon features so the buffered area is a specified percentage of the original area
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

from PyQt4 import QtCore, QtGui
import qgis.core as qgis
from ui_bufferbypercentage import Ui_BufferByPercentage

import os


class BufferByPercentageDialog(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_BufferByPercentage()
        self.ui.setupUi(self)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.rdoBuffer.setChecked(True)
        self.ui.btnBrowse.clicked.connect(self.browse)
        self.ui.inputLayer.currentIndexChanged.connect(self.populateAttributes)
        
    def populateLayers( self ):
        myListA = []
        self.ui.inputLayer.clear()
        
        #myListA = ftu.getLayerNames( [ qgis.QGis.Polygon ] )
        mapLayers = qgis.QgsMapLayerRegistry.instance().mapLayers()
        polygonLayers = [mapLayers[layer] for layer in mapLayers
                         if mapLayers[layer].type() == qgis.QgsMapLayer.VectorLayer
                         and mapLayers[layer].geometryType() == qgis.QGis.Polygon]
        for layer in polygonLayers:
            self.ui.inputLayer.addItem( layer.name(), layer )

    def populateAttributes( self ):
        self.ui.dropdownPercentageField.clear()
        layerName = self.ui.inputLayer.currentText()
        if layerName != "":         
            layer = qgis.QgsMapLayerRegistry.instance().mapLayersByName(layerName)[0]
            fieldList = [field.name()
             for field in list(layer.dataProvider().fields())
             if field.type() in (QtCore.QVariant.Double, QtCore.QVariant.Int)]
            self.ui.dropdownPercentageField.addItems(fieldList) 

    def browse( self ):
        fileName = QtGui.QFileDialog.getSaveFileName(self, 'Open file', 
                                        "", "Shapefile (*.shp);;All files (*)")
        fileName = os.path.splitext(str(fileName))[0]+'.shp'
        layername = os.path.splitext(os.path.basename(str(fileName)))[0]
        if (layername=='.shp'):
            return
        self.ui.outputLayer.setText(fileName)
        