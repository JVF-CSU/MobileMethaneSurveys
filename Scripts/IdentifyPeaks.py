###
# Requires Python 2.7 and ArcGIS API
# Identify Peaks in Methane
# Originally written by Dave Theobald, following logic of Jessica Salo from "peak_algorithm_30July2013.py"
# Updated by Duck Keun Yang from Colorado State University
###

### NEED TO CHANGE PARAMTERS in MAIN FUNCTION before excute.

import os, sys, datetime, time, math
import csv, numpy
from math import radians, sin, cos, sqrt, asin


def haversine(lat1, lon1, lat2, lon2, radius=6371): # 6371 = earth radius in kilometers
    # calculates haversine distance
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    c = 2*asin(sqrt(sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2))
    return radius*c*1000 # return in meters


def IdentifyPeaks( xCar, xDate, xDir, xFilename, xOutDir):
    """
    Identifies peaks for both methane and ethane based on the data produced by ProcessRawData. Writes the result to disk
    :param xCar: id of the car (example: 'CFADS2274')
    :param xDate: date of the file (example: '20160412')
    :param xDir: input directory path where the processed data file is present. Use only forward slashes
                  (example: 'D:/Data' or '/user/data')
    :param xFilename: name of the file (example: 'CFADS2274_20170314_dat.csv')
    :param xOutDir: output directory path to store the processed data. Optional.
                         default is same as input directory
    :return: None
    """
    try:
        if xOutDir is None:
            xOutDir = xDir + "/IdentifyPeaks"
        # check if the directory already exists and create if it does not.
        if not os.path.exists(xOutDir):
            os.makedirs(xOutDir)

        xABThreshold = 0.1 # above baseline threshold above the mean value
        xDistThreshold = 160.0 # find the maximum CH4 reading of observations within street segments of this grouping distance in meters
        xSDF = 4 # multiplier times standard deviation for floating baseline added to mean
        xB = 1020 # the number of records that constitutes the floating baseline time -- 7200 = 1 hour (assuming average of 0.5 seconds per record)
        xTimeThreshold = 5.0
        #xCity = "FC"; xLonMin = -105.171; xLatMin = 40.465; xLonMax = -104.978; xLatMax = 40.653 # city abbreviation and bounding box in geographic coordinates
        xCity = "US"; xLonMin = -126.0; xLatMin = 24.5; xLonMax = -65.0; xLatMax = 50.0 # city abbreviation and bounding box in geographic coordinates
        
        fn = xDir + "/" + xFilename      #set raw text file to read in
        fnOut = xOutDir + "Peaks" + "_" + xCar + "_" + xDate + ".csv"       #set CSV format output for observed peaks for a given car, day, city
        fnLog = xOutDir + "Peaks" + "_" + xCar + "_" + xDate + ".log"       #set CSV output for observed peaks for a given car, day, city
        fLog = open(fnLog, 'w')
        fnPoints = xDir + "Location" + "_" + xCar + ".csv"       #set CSV output for x,y locations of cars by days
        fPoints = open(fnPoints, 'a')

        #field column indices for various variables
        index = dict(fFracDays = 2, fFracHours = 3, fEpochTime = 5, fAlarm = 6, fCavP = 8, fCavT = 9, fWarmBoxT = 12, fCH4 = 19, fLat = 22, fLon = 23, fWKT = 35)

        #read data in from text file and extract desired fields into a list, padding with 5 minute and hourly average
        x1 = []; x2 = []; x3 = []; x4 = []; x5 = []; x6 = []; x7 = []

        count = 0
        cntOutside = 0
        with open(fn, 'rb') as f:
            t = csv.reader(f)
            for row in t:
                if count == 0:
                    fieldName1 = row[index['fFracHours']]; fieldName2 = row[index['fCH4']]; fieldName3 = row[index['fLat']]; fieldName4 = row[index['fLon']]; 
                else:
                    tCoord = row[index['fWKT']].split()
                    x1.append(float(row[index['fFracHours']])); x2.append(float(row[index['fCH4']])); x3.append(float(tCoord[1][:-1])); x4.append(float(tCoord[0][6:])); x5.append(0.0); x6.append(float(row[index['fEpochTime']])), x7.append(0.0)
                count += 1
        #print "Number of points outside the specified city's bounding box: " + str(cntOutside)
        print "Number of observations processed: " + str(count)
        #convert lists to numpy arrays
        aFracHours = numpy.array(x1); aCH4 = numpy.array(x2); aLat = numpy.array(x3); aLon = numpy.array(x4); aMean = numpy.array(x5); aEpochTime = numpy.array(x6); aThreshold = numpy.array(x7)
        
        # find observations with CH4 greater than mean+t -- Above Baseline

        '''
        if xCH4SD < (0.1 * xCH4Mean):
            xCH4SD = (0.1 * xCH4Mean)      # ensure that SD is at least ~0.2
        '''

        xLatMean = numpy.mean(aLat)
        xLonMean = numpy.mean(aLon)
        
        fLog.write ( "Day CH4_mean = " + str(numpy.mean(aCH4)) + ", Day CH4_SD = " + str(numpy.std(aCH4)) + "\n")
        fLog.write( "Center lon/lat = " + str(xLonMean) + ", " + str(xLatMean) + "\n")
        
        lstCH4_AB = []

        xCH4Mean = numpy.mean(aCH4[0:xB])       # initial floating baseline
        xCH4SD = numpy.std(aCH4[0:xB])

        #generate list of the index for observations that were above the threshold
        for i in range(0,count-2):
            if ((count-2)>xB):
                topBound = min((i+xB), (count-2))
                botBound = max((i-xB), 0)

                for t in range(min((i+xB), (count-2)), i, -1):
                    if aEpochTime[t] < (aEpochTime[i]+(xB/2)):
                        topBound = t
                        break
                for b in range(max((i-xB), 0), i):
                    if aEpochTime[b] > (aEpochTime[i]-(xB/2)):
                        botBound = b
                        break

                xCH4Mean = numpy.percentile(aCH4[botBound:topBound], 50) # 50th percentile as moving threshold
                xCH4SD = numpy.std(aCH4[botBound:topBound])
            else:
                xCH4Mean = numpy.percentile(aCH4[0:(count-2)], 50)
                xCH4SD = numpy.std(aCH4[0:(count-2)])

            xThreshold = xCH4Mean + (xCH4Mean * 0.1)

            if (aCH4[i] > xThreshold):
                lstCH4_AB.append(i)
                aMean[i] = xCH4Mean    #insert mean + SD as upper quartile CH4 value into the array to later retreive into the peak calculation
                aThreshold[i] = xThreshold
        
        # now group the above baseline threshold observations into groups based on distance threshold
        lstCH4_ABP = []
        lstPeakArea = []
        xDistPeak = 0.0
        xCH4Peak = 0.0
        xTime = 0.0
        cntPeak = 0
        cnt = 0
        cntStart = 0
        sID = ""
        sPeriod5Min = ""
        prevIndex = 0
        for i in lstCH4_AB:    
            if (cnt == 0):
                xLon1 = aLon[i]; xLat1 = aLat[i]
            else:
                # calculate distance between points
                xDist = haversine(xLat1, xLon1, aLat[i], aLon[i])
                xDistPeak += xDist
                xCH4Peak += (xDist * (aCH4[i] - aMean[i]))
                xLon1 = aLon[i]; xLat1 = aLat[i]
                if (sID == ""):
                    xTime = aFracHours[i]
                    sID = str(xCar) + "_" + str(xDate) + "_" + str(xTime)
                    sPeriod5Min = str(int((aEpochTime[i] - 1350000000) / (30 * 1))) # 30 sec
                if ((aEpochTime[i]-aEpochTime[prevIndex]) > xTimeThreshold):       #initial start of a observed peak
                    cntPeak += 1
                    xTime = aFracHours[i]
                    xDistPeak = 0.0
                    xCH4Peak = 0.0
                    sID = str(xCar) + "_" + str(xDate) + "_" + str(xTime)
                    sPeriod5Min = str(int((aEpochTime[i] - 1350000000) / (30 * 1))) # 30 sec
                    #print str(i) +", " + str(xDist) + "," + str(cntPeak) +"," + str(xDistPeak)         
                lstCH4_ABP.append([sID, xTime, aFracHours[i], aEpochTime[i], aCH4[i], "POINT(" + str(aLon[i]) + " " + str(aLat[i]) + ")", aLon[i],aLat[i],aMean[i],aThreshold[i], xDistPeak, xCH4Peak, sPeriod5Min])
            cnt += 1
            prevIndex = i
        
        # Finding peak_id larger than 160.0 m
        tmpsidlist = []
        for r in lstCH4_ABP:
            if (float(r[10])>160.0) and (r[0] not in tmpsidlist):
                tmpsidlist.append(r[0])
        cntPeak-=len(tmpsidlist)

        fLog.write ( "Number of peaks found: " + str(cntPeak) + "\n")
        fPoints.write(str(xCar) + "," + str(xDate) + "," + str(xLonMean) + "," + str(xLatMean) +"," + str(count) + "," + str(numpy.mean(aCH4)) + "," + str(xCH4SD) + "," + str(cntPeak) + ",POINT(" + str(xLonMean) + " " + str(xLatMean) + ")\n")
        print xCar + "\t" + xDate + "\t" + xFilename + "\t" + str(count) + "\t" + str(cntPeak)
        #### calculate attribute for the area under the curve -- PPM
        
        #write out the observed peaks to a csv to be read into a GIS
        fOut = open(fnOut, 'w')
        #s = "PEAK_NUM,FRACHRSTART," + fieldName1 + "," + fieldName2 + "," + fieldName3 + "," + fieldName4 + ',CH4_MEAN,PEAK_DIST_M,PEAK_CH4\n'
        s = "PEAK_NUM,FRACHRSTART," + fieldName1 + ",EPOCHTIME," + fieldName2 + ",WKT" + ',LON,LAT,CH4_BASELINE,CH4_THRESHOLD,PEAK_DIST_M,PEAK_CH4,PERIOD5MIN\n'
        fOut.write(s)

        for r in lstCH4_ABP:
            if r[0] not in tmpsidlist:
                s = ''
                for rr in r:
                    s += str(rr) + ','
                s = s[:-1]
                s += '\n'
                #print str(s)
                fOut.write(s)
        fOut.close()
        fLog.close()
        fPoints.close()
        
        return True
    except ValueError:
        print "Error in Identify Peaks"
        return False

def batch_identify(in_dir_path, out_dir_path=None, select_cars=[]):
    """
    Calls the identify_peaks function repeatedly for every data file in the given directory that matches the defined
    criteria
    :param in_dir_path: directory path where the processed data files are present
    :param out_dir_path: directory path to store the results. Optional. default is same as the input.
    :param select_cars: list of car ids to filter the files. only files containing the car ids in this list will be
    considered. Optional. Default value is empty - no filtering happens
    """

    if out_dir_path is None:
        out_dir_path = in_dir_path

    for filename in os.listdir(in_dir_path):
        names = filename.split('_')
        # Assumes file names are of type <some text>_<car id>_<date>_<file number>
        # file names may end with .txt or .txt.zip
        if len(names) != 3:
            print 'Skipping the file - ' + filename
            continue
        # names[2] should equal dat.csv to proceed with the processing
        if (len(select_cars) == 0 or names[0] in select_cars) and names[2] == 'dat.csv':
            print 'Processing the data file - ' + filename
            IdentifyPeaks(names[0], names[1], in_dir_path, filename, out_dir_path)
        else:
            print 'Skipping the file - ' + filename


if __name__ == '__main__':
    # select cars is optional. If you don't want to filter, remove the parameter or
    # send empty list as select_cars=[]
    # batch_process('input dir', 'out dir', 'car list')
    batch_identify('C:/Users/VonFischer/Documents/Methane/CodeForPublic/ProcessedRawData/',
                  'C:/Users/VonFischer/Documents/Methane/CodeForPublic/IdentifiedPeaks/',
                  select_cars=['CFADS2274', 'CFADS2280', 'CFADS2276'])