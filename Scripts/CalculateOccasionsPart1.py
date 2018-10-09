###
# Requires Python 2.7 and ArcGIS API
# Coverts ProcessedRawData into ArcGIS shapefile
# Orignially written by Adam Gaylord
# Updated by Duck Keun Yang from Colorado State University
###

### NEED TO CHANGE PARAMTERS before excute.

import arcpy
from arcpy.sa import *
from arcpy import env

## parameters to change
# List of days that will be converted into shapefile
lstCFADS2274 = [20170314, 20170315, 20170316, 20170317, 20170322,
                20170323, 20170324, 20170325]
# input directory where processed raw data are
sDir = 'C:/Users/VonFischer/Documents/Methane/CodeForPublic/ProcessedRawData/' 
sCity = "BIR"
sCar = "CFADS2274_"  # CFADS2280, CFADS2274, CFADS2276

for i in lstCFADS2274:
    fnIn = sDir + sCar + str(i)
    fnOut = sDir + sCity + sCar + str(i)
    print fnIn + " observations..."
    
    #make observations shapefiles
    arcpy.MakeXYEventLayer_management(fnIn + "_dat.csv","GPS_ABS_LONG","GPS_ABS_LAT",sCar + str(i) + "O","GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision","#")
    arcpy.FeatureToPoint_management(sCar + str(i) + "O", fnOut + ".shp","CENTROID")

    #calculate time period (every 5 minutes is a new one...)
    arcpy.AddField_management(fnOut + ".shp","Period5Min","LONG","#","#","#","#","NULLABLE","NON_REQUIRED","#")
    arcpy.CalculateField_management(fnOut + ".shp","Period5Min","([EPOCH_TIME] - 1350000000) / (30 * 1)","VB","#") # 30 seconds
    # convert to point at very fine resolution to allow different passes to pop through by chance

#THEN USE MANUAL MERGE OF NEWLY CREATED SHAPE FILES, SAVE AS <CITY>_AllOccasions<Date>