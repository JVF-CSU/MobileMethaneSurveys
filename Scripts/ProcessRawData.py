###
# Requires Python 2.7 and ArcGIS API
# Process raw data files, to:
# 1. combine by unique car and day combination
# 2. add car number as a field to the processed data...
# 3. data QA/QC steps:
#   a. remove if >45 mph
#   b. check for parameters out of specification for Picarro instrument
#   c. bad entries such as car speed: 1.#QNAN00000E+000 or -1.#IND000000E+000 or blank lines **send message to signify what file blank lines are in...
#   d. check for lat/long values of 0.0
#   e. adjusts x,y location for estimated time delay due to outlet pressure changes
# 4. write out as .csv to reduce file size and make ingesting into ArcGIS easier
# Orignially written by Dave Theobald, following logic of Jessica Salo from "raw_data_processing.py"
# Updated by Duck Keun Yang from Colorado State University
###

### NEED TO CHANGE PARAMTERS in MAIN FUNCTION before excute.

import os, sys, datetime, time, math, csv, numpy
from zipfile import ZipFile

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
def ProcessRawData( xCar, xDate, xDir, xFilename, gZIP, xOutDir):
    """
    Identifies peaks for both methane and ethane based on the data produced by ProcessRawData. Writes the result to disk
    :param xCar: id of the car (example: 'CFADS2274')
    :param xDate: date of the file (example: '20160412')
    :param xDir: input directory path where the processed data file is present. Use only forward slashes
                  (example: 'D:/Data' or '/user/data')
    :param xFilename: name of the file (example: 'CFADS2274-20170315-155022Z-DataLog_User.csv')
    :param xOutDir: output directory path to store the processed data. Optional.
                         default is same as input directory
    :return: None
    """
    try:
        # check if the directory already exists and create if it does not.
        if not os.path.exists(xOutDir):
            os.makedirs(xOutDir)

        maxCarSpeed = 45.0 / 2.23694     # assumes 45 mph as max, conver to meters per second       
        #data quality thresholds
        quality = dict(xCavPL=140.0-1, xCavPH=140.0+1,
                        xCavTL=45.0-1, xCavTH=45.0+1,
                        xWarmBoxTL = 45.0 - 1, xWarmBoxTH = 45.0 + 1,
                        xMinCarSpeed=0, xMaxCarSpeed=maxCarSpeed)
    
        #set up outlet-pressure delay parameters, specific to each car/instrument
        if xCar == "CFADS2274":
            # is car C10232
            xX2 = 0.00000006; xX1 = 0.0031; xX0 = 46.711; xOutletPressureLow = 19000; xOutletPressureHigh = 27000; xOutletPressureHighValue = 5.5; xDelay = 1.5
        elif xCar == "CFADS2280":
            # is car C10248
            xX2 = 0.00000004; xX1 = 0.0036; xX0 = 82.483; xOutletPressureLow = 32000; xOutletPressureHigh = 39000; xOutletPressureHighValue = 6.3; xDelay = 1.5   
        elif xCar == "CFADS2276":
            # is car C10258
            xX2 = 0.00000008; xX1 = 0.0044; xX0 = 61.386; xOutletPressureLow = 19000; xOutletPressureHigh = 24000; xOutletPressureHighValue = 4.8; xDelay = 1.5   
       
        # set header for fields
        #          0    1    2                    3                   4           5          6            7           8              9          10      11         12          13      14          15          16              17  18      19  20      21  22          23           24      25          26          27             28             29     30     31            32          33        34     35
        sHeader = 'DATE,TIME,FRAC_DAYS_SINCE_JAN1,FRAC_HRS_SINCE_JAN1,JULIAN_DAYS,EPOCH_TIME,ALARM_STATUS,INST_STATUS,CavityPressure,CavityTemp,DasTemp,EtalonTemp,WarmBoxTemp,species,MPVPosition,OutletValve,solenoid_valves,CO2,CO2_dry,CH4,CH4_dry,H2O,GPS_ABS_LAT,GPS_ABS_LONG,GPS_FIT,WS_WIND_LON,WS_WIND_LAT,WS_COS_HEADING,WS_SIN_HEADING,WIND_N,WIND_E,WIND_DIR_SDEV,WS_ROTATION,CAR_SPEED,CAR_ID,WKT,WIND_SPEED,WIND_DIRECTION\n'
        sHisHeader = 'CAR,DATE,CavPressMean,CavPressSTD,CavTempMean,CavTempSTD,WarmBTMean,WarmBTSTD,OutletPMean,OutletPSTD,CH4Mean,CH4STD,CarVelocityMean,CarVelocitySTD,WIND_NMean,WIND_EMean\n'
        # compile summary histogram data
        x8 = []; x9 = []; x12 = []; x15 = []; x19 = []; x22 = []; x23 = []; x30 = []; x31 = []; x33 = []
        
        #get all the files in the subdirectory
        #xDir2 = xDir + xCar         #+ "/" + xDate + "/"
        if gZIP:
            zip_file = ZipFile(xDir + "/" + xFilename)
            # opening text file inside zip file
            input_file = zip_file.open(xDir + "/" + xFilename)
            # reading all the lines in the text file
            rows = input_file.readlines()
        else:
            input_file = open(xDir + "/" + xFilename, 'r')
            rows = input_file.readlines()
        fnOut = xOutDir + xCar + "_" + xDate + "_dat.csv"       #set CSV output for raw data
        fnLog = xOutDir + xCar + "_" + xDate + "_log.csv"       #output for logfile
        fnHis = xOutDir + xCar + "_" + xDate + "_his.csv"       #set histogram output for raw data
        # if first time on this car/date, then write header out
        if os.path.exists(fnOut):
            fOut = open(fnOut, 'a')
        else:
            fOut = open(fnOut, 'w')
            fOut.write(sHeader)
        fLog = open(fnLog, 'a') if os.path.exists(fnLog) else open(fnLog, 'w')
        if os.path.exists(fnHis):
            fHis = open(fnHis, 'a')
        else:
            fHis = open(fnHis, 'w')
            fHis.write(sHisHeader)
        
        #read all lines
        xCntObs = 0
        xCntGoodValues = 0
        iDelay = 0
        for row in rows:
            bGood = True
            s1 = ""
            for i in range(0,34):
                xStart = i * 26
                xEnd = xStart + 26
                s2 = row[xStart:xEnd].replace(" ","")
                s1 += s2 + ","
                if (i > 1):
                    if not is_number(s2):
                        bGood = False
            if bGood:
                lstS = s1.split(",")
                # get raw values to summarize over each file, including GPS locations (22 = lat, 23 = long)
                x8.append(float(lstS[8])); x9.append(float(lstS[9])); x12.append(float(lstS[12])); x15.append(float(lstS[15])); x19.append(float(lstS[19])); x22.append(float(lstS[22])); x23.append(float(lstS[23])); x30.append(float(lstS[30])); x31.append(float(lstS[31])); x33.append(float(lstS[33]))
                
                #test for proper real values
                if float(lstS[19]) < 1.5:
                    fLog.write("CH4 value less than 1.5: "+ str(lstS[19]) + "\n")
                    continue
                if float(lstS[33]) > quality['xMaxCarSpeed']:
                    fLog.write("Car speed of " + str(float(lstS[33])) + " exceeds max threshold of: " + str(quality['xMaxCarSpeed']) + "\n")
                    continue
                if float(lstS[8]) < quality['xCavPL']:
                    fLog.write("Cavity Pressure " + str(lstS[8]) + " outside of range: " + str(quality['xCavPL']) + "\n")
                    continue
                if float(lstS[8]) > quality['xCavPH']:
                    fLog.write("Cavity Pressure " + str(float(lstS[8])) + " outside of range: " + str(quality['xCavPH']) + "\n")
                    continue
                if float(lstS[9]) < quality['xCavTL']:
                    fLog.write("Cavity Temperature " + str(float(lstS[9])) + " outside of range: " + str(quality['xCavTL']) + "\n")
                    continue
                if float(lstS[9]) > quality['xCavTH']:
                    fLog.write("Cavity Temperature " + str(float(lstS[9])) + " outside of range: " + str(quality['xCavTH']) + "\n")
                    continue
                if float(lstS[12]) < quality['xWarmBoxTL']:
                    fLog.write("Warm Box Temperature " + str(float(lstS[12])) + " outside of range: " + str(float(quality['xWarmBoxTL'])) + "\n")
                    continue
                if float(lstS[12]) > quality['xWarmBoxTH']:
                    fLog.write("Warm Box Temperature " + str(float(lstS[12])) + " outside of range: " + str(float(quality['xWarmBoxTH'])) + "\n")
                    continue
                #test for outlet pressure and adjust delay time/location based on function
                xOutletPressure = float(lstS[15])
                if xOutletPressure < xOutletPressureLow:
                    fLog.write("Outlet Pressure " + str(xOutletPressure) + " below minimum value: " + str(xOutletPressureLow) + "\n")
                    xTimeDelay = 0  ###????
                    continue
                elif xOutletPressure > xOutletPressureHigh:
                    xTimeDelay = xOutletPressureHighValue - xDelay
                else:
                    xTimeDelay = (xX2 * xOutletPressure * xOutletPressure) + (xX1 * xOutletPressure) + xX0 - xDelay
                ###
                
                #adjust the x,y location based on time delay. Assume 2 observations per second. Need to store the x,y locations in an array to access back in time.
                ####################################################################
                # WKT(Lat, Lon), this is the approximated true coordinates
                iDelay = xCntGoodValues - int(xTimeDelay * 2)
                if iDelay < 0:      # check to see if one of the beginning points... delay can't be before the first point
                    iDelay = 0
                s1 += xCar +",POINT(" + str(float(x23[iDelay])) + " " + str(float(x22[iDelay])) + "),"

                # Wind Speed Calculation
                s1 += str(math.sqrt( math.pow(float(lstS[29]),2) + math.pow(float(lstS[30]),2) )) + ","
                # Wind Direction Calculation
                s1 += str(180/math.pi*math.atan2(-float(lstS[29]), -float(lstS[30]))) + "\n"

                fOut.write(s1[:-1] + "\n")
                xCntGoodValues += 1
            xCntObs += 1
        sOut = str(gZIP) + "," + str(rows) + "," + str(xCntObs) + "," + str(xCntGoodValues) + "\n"
        fLog.write(sOut)
               
        fOut.close()
        fLog.close()
        
        #summarize info for histogram
        a8 = numpy.array(x8); a9 = numpy.array(x9); a12 = numpy.array(x12); a15 = numpy.array(x15); a19 = numpy.array(x19); a30 = numpy.array(x30); a31 = numpy.array(x31); a33 = numpy.array(x33)
        sHis = xCar + "," + xDate + "," + str(numpy.mean(a8)) + "," + str(numpy.std(a8)) + "," + str(numpy.mean(a9)) + "," + str(numpy.std(a9)) + "," + str(numpy.mean(a12)) + "," + str(numpy.std(a12)) + "," + str(numpy.mean(a15)) + "," + str(numpy.std(a15)) + "," + str(numpy.mean(a19)) + "," + str(numpy.std(a19)) + "," + str(numpy.mean(a33)) + "," + str(numpy.std(a33)) + "," + str(numpy.mean(a30)) + "," + str(numpy.mean(a31)) + "\n" 
        fHis.write(sHis)
        fHis.close()
        print xCar + "\t" + xDate + "\t" + xFilename + "\t" + str(xCntObs) + "\t" + str(xCntGoodValues) + "\t" + str(gZIP)
        
        return True
    except ValueError:
        return False


def batch_process(in_dir_path, out_dir_path, select_cars=[], select_zip=False):
    """
    Calls the process_raw_data function repeatedly for every file in the given directory that matches the defined
    criteria
    :param in_dir_path: directory path where the raw files are present
    :param out_dir_path: directory path to store the results
    :param select_cars: list of car ids to filter the files. only files containing the car ids in this list will be
    considered. Optional. Default value is empty - no filtering happens
    :param select_zip: whether to select zip files or any files. True to select only zip files, False otherwise. This
     parameter is optional. Default value is True - looks for zip files
    """
    for filename in os.listdir(in_dir_path):
        names = filename.split('-')
        # Assumes file names are of type <some text>_<car id>_<date>_<file number>
        # file names may end with .txt or .txt.zip
        if len(names) != 4:
            continue
        file_extension = filename[-3:]
        if len(select_cars) == 0 or names[0] in select_cars:
            print 'Processing the file - ' + filename
            if select_zip:
                if file_extension == 'zip':
                   ProcessRawData(names[0], names[1], in_dir_path, filename, True, out_dir_path)
                else:
                    print 'Skipping the file - ' + filename
            else:
                ProcessRawData(names[0], names[1], in_dir_path, filename, False, out_dir_path)
        else:
            print 'Skipping the file - ' + filename

if __name__ == '__main__':
    # select cars is optional. If you don't want to filter, remove the parameter or
    # send empty list as select_cars=[]
    # batch_process('input dir', 'out dir', 'car list')
    batch_process('C:/Users/VonFischer/Documents/Methane/CodeForPublic/SampleRawData/',
                  'C:/Users/VonFischer/Documents/Methane/CodeForPublic/ProcessedRawData/',
                  select_cars=['CFADS2274', 'CFADS2280', 'CFADS2276'])