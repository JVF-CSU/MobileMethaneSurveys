###
# Requires Python 2.7 and ArcGIS API
# Calculates verified peaks
# Detailed instruction can be found in the doc
# Orignially written by Adam Gaylord
# Updated by Duck Keun Yang from Colorado State University
###

### NEED TO CHANGE PARAMTERS  before excute.

import arcpy
import os
from arcpy.sa import *
from arcpy import env

from math import radians, sin, cos, sqrt, asin

#NEED TO: modify sDir, sCity, and sObs

## parameters to change
# List of days that will be converted into shapefile
lstCFADS2274 = [20170314, 20170315, 20170316, 20170317, 20170322,
                20170323, 20170324, 20170325]
# input directory where processed identified peaks are
sDir = 'C:/Users/VonFischer/Documents/Methane/CodeForPublic/IdentifiedPeaks/' 
# Output directory for shapefiles
sOutDir = 'C:/Users/VonFischer/Documents/Methane/CodeForPublic/Shapefiles/' 
sCity = "BIR"
sCar = "CFADS2274_"  # CFADS2280, CFADS2274, CFADS2276

#make peaks shapefiles
#for i in lstCFADS2274:
#for i in lstCFADS2276:
for i in lstCFADS2274:
    fnIn = sDir + "Peaks_" + sCar + str(i)
    fnOut = sDir + sCity + "Peaks_" + sCar + str(i)
    print fnIn + " peaks..."
    arcpy.MakeXYEventLayer_management(fnIn + ".csv","lon","lat",sCar + "L","GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision","#")
    arcpy.FeatureToPoint_management(sCar + "L",fnOut + ".shp","CENTROID")
    arcpy.Delete_management(sCar+"L")

#### MANUAL merge these files into "<city>_LeakPoints"

# now generate static leaks (aka verified peaks)
#summarize on Peak_Num and calculate stats, mean, std, min, etc.
fnLeakPoints = sOutDir + sCity + "_LeakPoints.shp" # All elevated readings
fnLeakPointsBuff = sOutDir + sCity + "LeakPointsBuff.shp"
fnLeakPointsSum = sOutDir + sCity + "LeakPointsSum.dbf"
fnLeakPointsCentroids = sOutDir + sCity + "AllLeakCentroids.shp"
fnStaticLeakPoints = sOutDir + sCity + "StaticLeakPoints.shp"

fnStaticLeakPointsBuff = sOutDir + sCity + "StaticLeakPointsBuff.shp"
fnStaticLeakPointsBuff2 = sOutDir + sCity + "StaticLeakPointsBuff2.shp"
fnStaticLeakPoints1Sum = sOutDir + sCity + "StaticLeakPointsSum1.dbf"
fnStaticLeakPoints2Sum = sOutDir + sCity + "StaticLeakPointsSum2.dbf"
fnStaticLeakPoints3Sum = sOutDir + sCity + "StaticLeakPointsSum3.dbf"
fnStaticLeakVerified = sOutDir + sCity + "StaticLeakBuffCentroids.dbf"
fnStaticLeakVerifiedFinal = sOutDir + sCity + "_StaticLeakBuffCentroidsFinal.dbf" # Verified Peaks
fnStaticLeakPoints2 = sOutDir + sCity + "_StaticLeakPoints2.shp" # Observed Peaks
'''

# 1. s'ummarize point attributes to each unique leak
arcpy.AddField_management(fnLeakPoints,"TempFID","TEXT","#","#","#","#","NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management(fnLeakPoints,"TempFID","!PEAK_NUM!+str(!CH4!)","PYTHON","#")
arcpy.Statistics_analysis(fnLeakPoints,fnLeakPointsSum,"CH4_BASELI MIN;PEAK_DIST_ MAX;PEAK_CH4 MAX;CH4 MEAN;CH4 STD;CH4 MAX;CH4 MIN;PEAK_DIST_ MAX;CH4_BASELI MEAN","PEAK_NUM") #summarize points for each peak num
arcpy.Buffer_analysis(fnLeakPoints,fnLeakPointsBuff,"30 Meters","FULL","ROUND","LIST","PEAK_NUM")   #find points of peaks that are within 20 m and dissolve on Peak Number
arcpy.JoinField_management(fnLeakPointsBuff,"PEAK_NUM",fnLeakPointsSum,"PEAK_NUM","FREQUENCY;MIN_CH4_BA;MAX_PEAK_D;MAX_PEAK_C;MEAN_CH4;STD_CH4;MAX_CH4;MIN_CH4;MEAN_CH4_B")   #join summarized stats to buffered peaks

# 2. Leak buffers to centroids
arcpy.FeatureToPoint_management(fnLeakPointsBuff,fnLeakPointsCentroids,"INSIDE")    #convert buffered peaks to single point at the centroid
arcpy.AddField_management(fnLeakPointsCentroids,"PPMM","DOUBLE","#","#","#","#","NULLABLE","NON_REQUIRED","#")    #add field to calculate PPMM - CH4 parts per million per meter
arcpy.CalculateField_management(fnLeakPointsCentroids,"PPMM","[MAX_PEAK_D] * ([MEAN_CH4] - [MIN_CH4_BA])","VB","#")    # calculate PPMM as a function of (mean CH4 - baseline ) * distance of peak
arcpy.AddField_management(fnLeakPointsCentroids,"D","TEXT","10")
arcpy.CalculateField_management(fnLeakPointsCentroids,"D","Right(Left( [PEAK_NUM], 18), 8)","VB","#")   # calculate using yyyymmdd format
#arcpy.CalculateField_management(fnLeakPointsCentroids,"Date","""!PEAK_NUM![14:16] + "/" + !PEAK_NUM![16:18] + "/" + !PEAK_NUM![10:14] ""","PYTHON","#")     # calculate using mm/dd/yyyy format
arcpy.AddField_management(fnLeakPointsCentroids,"TempRate","DOUBLE","#","#","#","#","NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management(fnLeakPointsCentroids,"TempRate","math.log(!MAX_CH4!-!MEAN_CH4_B!)","PYTHON","#")

# 3. Leak centroids to StaticLeakCentroid
arcpy.Select_analysis(fnLeakPointsCentroids,fnStaticLeakPoints,""""MAX_PEAK_D" > 0.1 AND "MAX_PEAK_D" < 160 """)  #remove peaks that have a single point because they have distance = 0, and remove dist > 160 m because likely not a static leak source (i.e. AREA peak)
arcpy.AddField_management(fnStaticLeakPoints,"FlowRate","DOUBLE","#","#","#","#","NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management(fnStaticLeakPoints,"FlowRate","1.0**(0.06505 + (0.06925 * !MAX_CH4!) + (-0.004516 * !PPMM!) + (!MAX_CH4! - 8.28999) * ((!PPMM! - 137.6) * 0.000051747) + (0.081365 * (!PPMM!  / !MAX_CH4!)))","PYTHON","#")

# 4. Static leak centroids
arcpy.Buffer_analysis(fnStaticLeakPoints,fnStaticLeakPointsBuff,"30 Meters","FULL","ROUND","ALL","#")
arcpy.MultipartToSinglepart_management(fnStaticLeakPointsBuff,fnStaticLeakPointsBuff2)
arcpy.CalculateField_management(fnStaticLeakPointsBuff2,"ORIG_FID","[FID]","VB","#")

# 5 Manually spacially join fnStaticLeakPoints and fnStaticLeakPointsBuff2 (IN THIS ORDER!)
#Select from folder, not drop down
#Save into same sDir directory as fnStaticLeakPoints2
#Should be points, not area
#arcpy.SpatialJoin_analysis(fnStaticLeakPoints,fnStaticLeakPointsBuff2,fnStaticLeakPoints2,"JOIN_ONE_TO_ONE","KEEP_ALL","""PEAK_NUM "PEAK_NUM" true true false 254 Text 0 0 ,First,#,FTC_StaticLeakPoints,PEAK_NUM,-1,-1;FREQUENCY "FREQUENCY" true true false 9 Long 0 9 ,First,#,FTC_StaticLeakPoints,FREQUENCY,-1,-1;MIN_CH4_BA "MIN_CH4_BA" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,MIN_CH4_BA,-1,-1;MAX_PEAK_D "MAX_PEAK_D" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,MAX_PEAK_D,-1,-1;MAX_PEAK_C "MAX_PEAK_C" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,MAX_PEAK_C,-1,-1;MEAN_CH4 "MEAN_CH4" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,MEAN_CH4,-1,-1;STD_CH4 "STD_CH4" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,STD_CH4,-1,-1;MAX_CH4 "MAX_CH4" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,MAX_CH4,-1,-1;MIN_CH4 "MIN_CH4" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,MIN_CH4,-1,-1;ORIG_FID "ORIG_FID" true true false 9 Long 0 9 ,First,#,FTC_StaticLeakPoints,ORIG_FID,-1,-1;PPMM "PPMM" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,PPMM,-1,-1;Date "Date" true true false 9 Long 0 9 ,First,#,FTC_StaticLeakPoints,Date,-1,-1;FlowRate "FlowRate" true true false 19 Double 0 0 ,First,#,FTC_StaticLeakPoints,FlowRate,-1,-1;Id "Id" true true false 6 Long 0 6 ,First,#,FTC_StaticLeakPointsBuff2,Id,-1,-1;ORIG_FID_1 "ORIG_FID_1" true true false 9 Long 0 9 ,First,#,FTC_StaticLeakPointsBuff2,ORIG_FID,-1,-1""","INTERSECT","#","#")

# 6. Clusters of leaks (verified peaks)

arcpy.AddField_management(fnStaticLeakPoints2,"TempFID","TEXT","#","#","#","#","NULLABLE","NON_REQUIRED","#")
arcpy.CalculateField_management(fnStaticLeakPoints2,"TempFID","!PEAK_NUM!+str(!MAX_CH4!)","PYTHON","#")
arcpy.JoinField_management(fnStaticLeakPoints2,"TempFID",fnLeakPoints,"TempFID","LAT; LON")

pnt = arcpy.Point()
rows = arcpy.UpdateCursor(fnStaticLeakPoints2)
for row in rows:
    pnt.X = row.LON
    pnt.Y = row.LAT
    row.shape = pnt
    rows.updateRow(row)
del row, rows


arcpy.AddField_management(fnStaticLeakPoints2, "LMEAN_CH4", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")
arcpy.CalculateField_management(fnStaticLeakPoints2, "LMEAN_CH4", "math.log(!MEAN_CH4!,10)", "PYTHON", "#")

arcpy.Statistics_analysis(fnStaticLeakPoints2,fnStaticLeakPoints1Sum,"MAX_CH4 SUM; ","ORIG_FID_1")
arcpy.JoinField_management(fnStaticLeakPoints2,"ORIG_FID_1",fnStaticLeakPoints1Sum,"ORIG_FID_1","SUM_MAX_CH")

arcpy.AddField_management(fnStaticLeakPoints2, "wLat", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")
arcpy.CalculateField_management(fnStaticLeakPoints2, "wLat", "(!MAX_CH4!/!SUM_MAX_CH!) * !SHAPE!.centroid.Y", "PYTHON", "#")
arcpy.AddField_management(fnStaticLeakPoints2, "wLon", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")
arcpy.CalculateField_management(fnStaticLeakPoints2, "wLon", "(!MAX_CH4!/!SUM_MAX_CH!) * !SHAPE!.centroid.X", "PYTHON", "#")

arcpy.Statistics_analysis(fnStaticLeakPoints2,fnStaticLeakPoints3Sum,"wLat SUM; wLon SUM","ORIG_FID_1")
arcpy.JoinField_management(fnStaticLeakPoints2,"ORIG_FID_1",fnStaticLeakPoints3Sum,"ORIG_FID_1","SUM_wLat; SUM_wLon")

arcpy.AddField_management(fnStaticLeakPoints2, "adRate", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")

expression = "(!TempRate!+0.593882+(0.072154*haversinemod(!SUM_wLat!, !SUM_wLon!, !SHAPE!.centroid.Y,!SHAPE!.centroid.X)))/0.947231"

codeblock = """from math import radians, sin, cos, sqrt, asin
def haversinemod(lat1, lon1, lat2, lon2, radius=6371):
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    c = 2*asin(sqrt(sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2))
    result = radius*c*1000.0
    if result > 30.0:
        return 30.0
    else:
        return result"""

arcpy.CalculateField_management(fnStaticLeakPoints2, "adRate", expression, "PYTHON", codeblock)

arcpy.Statistics_analysis(fnStaticLeakPoints2,fnStaticLeakPoints2Sum,"D MIN;D MAX;PPMM MEAN;MAX_CH4 MEAN;MIN_CH4_BA MEAN;FlowRate MEAN;LMEAN_CH4 MEAN; MAX_CH4 SUM; wLat SUM; wLon SUM; TempRate MEAN; adRate MEAN","ORIG_FID_1")
arcpy.FeatureToPoint_management(fnStaticLeakPointsBuff2,fnStaticLeakVerified,"INSIDE")    #convert buffered peaks to single point at the centroid
arcpy.JoinField_management(fnStaticLeakVerified,"ORIG_FID",fnStaticLeakPoints2Sum,"ORIG_FID_1","FREQUENCY;MIN_D;MAX_D;MEAN_PPMM;MEAN_MAX_C;MEAN_MIN_C;MEAN_FlowR;MEAN_LMEAN;MEAN_TempR;SUM_wLat;SUM_wLon; MEAN_adRat")
arcpy.AddField_management(fnStaticLeakVerified,"First_Date","TEXT","10")
arcpy.AddField_management(fnStaticLeakVerified,"Last_Date","TEXT","10")
arcpy.CalculateField_management(fnStaticLeakVerified,"First_Date","""!MIN_D![4:6] + "/" + !MIN_D![6:8] + "/" + !MIN_D![0:4] ""","PYTHON","#")     # calculate using mm/dd/yyyy format
arcpy.CalculateField_management(fnStaticLeakVerified,"Last_Date","""!MAX_D![4:6] + "/" + !MAX_D![6:8] + "/" + !MAX_D![0:4] ""","PYTHON","#")     # calculate using mm/dd/yyyy format
arcpy.AddField_management(fnStaticLeakVerified, "LeakSizeE", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")
arcpy.CalculateField_management(fnStaticLeakVerified, "LeakSizeE", "10**(-0.5314+2.6862*!MEAN_LMEAN!)", "PYTHON", "#")
arcpy.AddField_management(fnStaticLeakVerified, "FlowRate2", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")
arcpy.CalculateField_management(fnStaticLeakVerified, "FlowRate2", "math.exp((!MEAN_TempR!+0.9881882)/(0.8166417))", "PYTHON", "#")
arcpy.AddField_management(fnStaticLeakVerified, "FlowRate3", "DOUBLE", "#", "#", "#", "#", "NULLABLE", "NON_REQUIRED", "#")
arcpy.CalculateField_management(fnStaticLeakVerified, "FlowRate3", "math.exp(!MEAN_adRat!)", "PYTHON", "#")
arcpy.Select_analysis(fnStaticLeakVerified,fnStaticLeakVerifiedFinal,""""FREQUENCY" > 1 """)  #remove peaks that are not verified, i.e. FREQUENCY = 1

pnt = arcpy.Point()
rows = arcpy.UpdateCursor(fnStaticLeakVerifiedFinal)
for row in rows:
    pnt.X = row.SUM_wLon
    pnt.Y = row.SUM_WLat
    row.shape = pnt
    rows.updateRow(row)
del row, rows
'''