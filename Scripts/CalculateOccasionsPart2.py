###
# Requires Python 2.7 and ArcGIS API
# Calculates number of passes for each road point
# Road points file is generated based on Tiger Road shapefile (using lines to points function in ArcMap)
# Detailed instruction can be found in the doc
# Orignially written by Adam Gaylord
# Updated by Duck Keun Yang from Colorado State University
###

### NEED TO CHANGE PARAMTERS  before excute.

import arcpy
from arcpy.sa import *
from arcpy import env

## Parameters to change
# # input directory where shape files are
sDir = "C:/Users/VonFischer/Documents/Methane/CodeForPublic/Shapefiles/"
sCity = "BIR"
fnRoads = sDir + sCity + "_RoadPoints.shp" # RoadPoints file
fnObs = sDir + sCity + "_AllOccasions.shp" # AllOccasions from Part1 Script
fnOutTable = sDir + "PD_" + sCity + "_roads_v_occ4.dbf"

arcpy.PointDistance_analysis(fnRoads,fnObs,fnOutTable,"20 Meters")

# join
arcpy.JoinField_management(fnOutTable,"NEAR_FID",fnObs,"FID","Period5Min")

print "Calculating number of occasions..."
lstOut = []
lstID = []
xOldRoadID = -999
lstV = []
cursor = arcpy.SearchCursor(fnOutTable)
for row in cursor:
    xRoadID = row.getValue("Input_FID")
    if xRoadID != xOldRoadID:
        xOldRoadID = xRoadID
        #print str(xRoadID) + ", " + str(len(set(lstV)))
        lstOut.append(len(set(lstV)))       #get the count of unique values in the list, equals # of observations/passes
        lstV = []
        lstID.append(xRoadID)
    lstV.append(row.getValue("Period5Min"))
del row, cursor

print "Assigning number of occasions back to road points..."
#assign occasions back to road points
arcpy.AddField_management(fnRoads,"NumOccs","LONG","#","#","#","#","NULLABLE","NON_REQUIRED","#")
cursor = arcpy.UpdateCursor(fnRoads)
i = 0
j = len(lstID)
for row in cursor:
    if i < j:
        x1 = row.getValue("FID")
        #print str(x1) + ", " + str(i)
        if lstID[i] == x1:
            row.setValue("NumOccs", lstOut[i])
            cursor.updateRow(row)
            i += 1
del row, cursor


