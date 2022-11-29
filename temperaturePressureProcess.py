#!/usr/bin/python3

# Simple method that should be launched in a separate process and should measure the temperatures T1, T2, T3, T4 and the pressure P1, P2, P3, P4 every x Second. 
#   Analog Pressure Sensor: 0 - 5V, 0 - 10 Bar, ADC-12bits 
#   Temperature sensor: Type NTC 10K B=3435 
#   
# 
# @Programmer: A. M.
# @ Date: 12-06-2019
# 


import time
import datetime
import threading
import re, os, time , sys, math
import signal
import array as arr
from multiprocessing import Process, Pipe, Array, Value

# Import the ADS1x15 module.
#import Adafruit_ADS1x15				     # ADC ADS1x15

import glob
import smbus
from MCP342x import MCP342x
from lib_python_logging import * 



class CLS_Drinko_DEVICE:
    DEVICE_ID = 355
    NBR_TURBINES = 2
    POWER_SENSOR = 30




TempPress = Array('d', range(9))         # Temperature and Pressure measurements - Global shared inter-process variables

#-----------------------------------------------------------------------  
        
# Logger object to log our events, data etc.
ttpp_logger = get_logger("SNOW-539")



def get_smbus():
    candidates = []
    prefix = '/dev/i2c-'
    for bus in glob.glob(prefix + '*'):
        try:
            n = int(bus.replace(prefix, ''))
            candidates.append(n)
        except:
            pass

    if len(candidates) == 1:
        return smbus.SMBus(candidates[0])
    elif len(candidates) == 0:
        raise Exception("Could not find an I2C bus")
    else:
        raise Exception("Multiple I2C busses found")


bus = get_smbus()

print("\n MCP3424 ADC-18bits initialisation:")

# Create objects for each signal to be sampled
addr68_ch0 = MCP342x(bus, 0x68, channel=0, resolution=18, gain=1)
addr68_ch1 = MCP342x(bus, 0x68, channel=1, resolution=18, gain=1)
addr68_ch2 = MCP342x(bus, 0x68, channel=2, resolution=18, gain=1)
addr68_ch3 = MCP342x(bus, 0x68, channel=3, resolution=12, gain=2)

addr69_ch0 = MCP342x(bus, 0x69, channel=0, resolution=18, gain=1)
addr69_ch1 = MCP342x(bus, 0x69, channel=1, resolution=18, gain=1)
addr69_ch2 = MCP342x(bus, 0x69, channel=2, resolution=18, gain=1)
addr69_ch3 = MCP342x(bus, 0x69, channel=3, resolution=18, gain=1)

adc_temp = [addr69_ch0, addr69_ch1, addr69_ch2, addr69_ch3 ]    #
print(adc_temp)
adc_press = [addr68_ch0, addr68_ch1, addr68_ch2 ]   #
print(adc_press)
adc_pow = addr68_ch3
print("\n")


#---------------------------------------------------------------------
# ADC 18bits MCP3424 ------------------------------------------------
# Max input voltage
ADC_MAX_VOLTAGE_IN = 2.048 # Differential input voltage +- 2.048 [V]

# Half full-range 17 bits :    131071 Steps    0x1FFFF   --> 17bits
ADC_MAX_STEPS = 131071      # Steps
 
ADC_LSB = ADC_MAX_VOLTAGE_IN / ADC_MAX_STEPS   # 15.625UV (Resolution 18bits)
ADC_LSB_12 = ADC_MAX_VOLTAGE_IN / 2047.0       # 2.048 V / 2047 ~1mv
#---------------------------------------------------------------------

# Number of samples
NBR_SAMPLES = 15   # Average measurements (temperature and pressure).


#---------------------------------------------------------------------
# Sensor Pressure transmitter (0 - 10 Bar)
# Model: WNK83MA 
# Power: 5V DC 
# Output: 0.5-4.5V 
# Range: 0-10bar
# SN:X200xxx

# Resistors to convert [0, 5V] to --> [0, 2.02380V] : Pressure Input 
R57 = 10                   # R57 = R58 = R59 = R60 = 10 KOhm
R64 = 6.8                  # R64 = R63 = R62 = R61 = 6.8 KOhm 

# Coefficient and Constant (Pressure input)
Kc = (R57+R64)/R64      #  Kc ~ 1/0.4047  ~ 2.47058

# Calibration parameters
m_press = 9.626617 * 1e-05
p_press = -1.251781574

ADC_Press_Steps = [0,0,0,0]
ADC_Press_Voltages = [0,0,0,0]
WNK83MA_Pressure = [999.9, 999.9, 999.9, 999.9]
POWER = [999.9]
#----------------------------------------------------------------------

OFFSET_ERROR_PERCENT = 0.05   # 5% Error on the voltage reading Power

#---------------------------------------------------------------------
# Temperature Sensor parameters  
# Coefficient NTC B3534K 
#-----------------------------------------------
# Steinhart-Hart Equation 
# 1/T = a + b(Ln R) + c(Ln R)^3
#-----------------------------------------------
a = 0.000891865
b = 0.000250180
c = 0.000000202
#-----------------------------------------------

VRefTemp = 3.0  # 3.0 Volt, LM4128AMF
R53 = 1.5       # KOhm  R53=R54=R55=R56=1.5KOhm

ADC_Temp_Steps = [0,0,0,0]; 
ADC_Temp_Voltages = [0,0,0,0]; 
NTC_Resistors = [0,0,0,0]; 
NTC_Temperatures = [999.9, 999.9, 999.9, 999.9]
#----------------------------------------------------------------------




def tempPressPowerMethod(VOLT_TO_AMP = 30):   # Default 30A <==> 1 V
    
    '''# ADC ADS1015 12 bits 
    adc = Adafruit_ADS1x15.ADS1015()
    adc_2 = Adafruit_ADS1x15.ADS1015(address=0x49, busnum=1)
    
    # Sensor Pressure transmitter (0 - 10 Bar)
    # Model: WNK83MA 
    # Power: 5V DC 
    # Output: 0.5-4.5V 
    # Range: 0-10bar
    # SN:X200xxx
    # Calibration parameters
    k_press1 = 0.00504254868512
    m_press1 = -1.2533309143329
    
    # Power consumption
    MAX_V = 0.0
    m = 0.256/2047.0  # Gain 16
    #m=4.096/2047.0   # Gain 1
    U_RMS = 230
    # Default 30A <==> 1 V   VOLT_TO_AMP = 30
    # Other possible sensors: 20A <==> 1V  or 10A <==> 1V
    
    
    # Choose a gain of 1 for reading voltages from 0 to 4.09V.
    # Or pick a different gain to change the range of voltages that are read:
    #  - 2/3 = +/-6.144V
    #  -   1 = +/-4.096V
    #  -   2 = +/-2.048V
    #  -   4 = +/-1.024V    
    #  -   8 = +/-0.512V
    #  -  16 = +/-0.256V
    # See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
    GAIN_P = 1
    GAIN_T = 4
    GAIN_POW = 16
    NBR_SAMPLES = 25   # Number of samples: Average measurements (temperature and pressure).'''
    
   
    while True: # infinite loop
        try:
            
            temp1 = 999.9; temp2 = 999.9; temp3 = 999.9; temp4 = 999.9;
            press1 = 999.9; press2 = 999.9; press3 = 999.9; press4 = 999.9; power4 = 999.9;
            
            #--------------------------------------------------------------------------------------
            # Read Pressure P1, P2, P3, P4 (Sensor Pressure transmitter 10 Bar, WNK83MA ADC12bits).
            
            '''values = [0,0,0,0]

            try:
                press_avg = 0; n=0
                while( n < NBR_SAMPLES  ):
                    #print("Pressure Start conversion ADC ***********")
                    values[0] = adc.read_adc(0, gain=GAIN_P)
                    #print("ADC 0 value : {}".format(values[0]))
                    press1 =  k_press1*values[0] + m_press1
                    #print("press1 {}".format(press1))
                    press_avg = press_avg + press1
                    n = n + 1
                press1 = press_avg/NBR_SAMPLES
                #print("Avg Press1 {} °C".format(press1))
            except Exception as e:
                press1 = 999.9 
                print("Exception Pressure P1 : " + str(e))
                
            try:
                press_avg = 0; n=0 
                while( n < NBR_SAMPLES ):
                    #print("Pressure Start conversion ADC ***********")
                    values[1] = adc.read_adc(1, gain=GAIN_P)
                    #print("ADC 1 value : {}".format(values[1]))
                    press2 = k_press1*values[1] + m_press1
                    #print("press2 {}".format(press2))
                    press_avg = press_avg + press2
                    n = n + 1
                press2 = press_avg/NBR_SAMPLES
                #print("Avg Press2 {} °C".format(press2))
            except Exception as e:
                press2 = 999.9 
                print("Exception Pressure P2 : " + str(e))
                
            try:
                press_avg = 0; n=0
                while( n < NBR_SAMPLES ):
                    #print("Pressure Start conversion ADC ***********")
                    values[2] = adc.read_adc(2, gain=GAIN_P)
                    #print("ADC 2 value : {}".format(values[2]))
                    press3 = k_press1*values[2] + m_press1
                    #print("press3 {}".format(press3))
                    press_avg = press_avg + press3
                    n = n + 1
                press3 = press_avg/NBR_SAMPLES
                #print("Avg Press3 {} °C".format(press3))
            except Exception as e:
                press3 = 999.9 
                print("Exception Pressure P3 : " + str(e))'''
                
                
            #--------------------------------------------------------------
            # Pressure ADC: Address 0x68
            start_time=time.time()
            for i in range(3): 
                #print("{} : Resolution: {} bits".format( i, adc_press[i].get_resolution()) )
                try:
                    press_avg = 0; n=0
                    while( n < NBR_SAMPLES  ):
                        #print("Pressure Start conversion ADC ***********")
                        adc_press[i].convert()
                        ADC_Press_Steps[i] = adc_press[i].raw_read()[0]
                        
                        ADC_Press_Voltages[i] = Kc * ADC_LSB * ADC_Press_Steps[i]
                        
                        press =  m_press * ADC_Press_Steps[i] + p_press 
                        press_avg = press_avg + press
                        n = n + 1
                    WNK83MA_Pressure[i] = press_avg/NBR_SAMPLES
                    #print("Avg Press {} [Bar]".format(WNK83MA_Pressure[i]))
                except Exception as e:
                    WNK83MA_Pressure[i] = 999.9
                    print("Exception Pressure P{} : {} ".format(i,e))
                
            print("Pressures: P1: {:05.2f}, P2: {:05.2f}, P3: {:05.2f}".format(WNK83MA_Pressure[0], WNK83MA_Pressure[1], WNK83MA_Pressure[2],))
            print("Voltages: V1: {:05.2f}, V2: {:05.2f}, V3: {:05.2f}".format(ADC_Press_Voltages[0], ADC_Press_Voltages[1], ADC_Press_Voltages[2]))
            print("Steps: Input1: {}, Input2: {}, Input3: {}".format(ADC_Press_Steps[0], ADC_Press_Steps[1], ADC_Press_Steps[2]))
            print(time.time()-start_time)
            print()
                
                
                
            '''try:
                
                MAX_V = 0.0
                P = 0.0
                I_RMS = 0.0
                V_RMS=0.0
                vout = 0.0
                t1=time.time()
                for i in range(1000):   # 100 x 0.2ms = 20ms 
                    # Read the specified ADC channel using the previously set gain value.
                    steps = adc.read_adc(3, gain=GAIN_POW)
                    vout = m*steps
                    
                    if(vout > MAX_V): 
                        MAX_V = vout
                    V_RMS = MAX_V/1.41421
                    I_RMS = V_RMS*VOLT_TO_AMP
                    P = U_RMS * I_RMS
                    power4 = P
                    #print("Power: {}".format(P))
                    
            except Exception as e:
                #press4 = 999.9
                power4 = 999.9
                print("Exception Power P4 : " + str(e))'''
                
                
                



            #--------------------------------------------------------------
            # Power sensor, Power consumption
            MAX_V = 0.0
            #VOLT_TO_AMP = CLS_Drinko_DEVICE.POWER_SENSOR #30
            # Default 30A <==> 1 V   VOLT_TO_AMP = 30
            # Other possible sensors: 20A <==> 1V  or 10A <==> 1V
            U_RMS = 230
            
            start_time = time.time()
            try:
                MAX_V = 0.0
                P = 0.0
                I_RMS = 0.0
                V_RMS=0.0
                vout = 0.0
                t1=time.time()
                for i in range(50):
                    for j in range(4):
                        #start_time = time.time()
                        adc_pow.convert()
                        steps=adc_pow.raw_read()[0]
                        #print(steps)
                        vout = abs( Kc * ADC_LSB_12*steps/2.0 )
                        #print(time.time()-start_time)
                        if(vout > MAX_V): 
                            MAX_V = vout
                    time.sleep(0.0001)
                    
                MAX_V = (1 + OFFSET_ERROR_PERCENT) * MAX_V
                V_RMS = MAX_V/1.41421
                I_RMS = V_RMS*VOLT_TO_AMP
                P = U_RMS * I_RMS
                POWER[0] = P
                #print(P)
                    
                print("Max V: {}".format(MAX_V))
                print("V_RMS V: {}".format(V_RMS))
                print("Power: {}".format(P))
                print(time.time()-start_time)
                print("-----------------\n")
                    
            except Exception as e:
                POWER[0] = 999.9
                print("Exception Power P4: ".format(e) )




                
                
            #--------------------------------------------------------------------------
            # Read temperatures T1, T2, T3, and T4 (4 probes x NTC 10K B3435 ADC12bits)
            
            '''try:
                temp_avg = 0; n=0
                while( n < NBR_SAMPLES ):
                    #print("Start Temperature 1 conversion ADC")
                    values[0] = adc_2.read_adc(0, gain=GAIN_T)
                    #print("NTC Resistor 1 ADC value : {:02.1f}".format(values[0]))
                    R2 = 1.5  # 1.5 KOhm
                    Vin = 3    # 3V Vref
                    vout = (values[0]/2047.0 )*1.024 #4.09
                    #print("Vout : {:02.3f}".format(vout))
                    R = R2 * ( (3.0 / vout) -1)
                    #print("Resistor R : {:02.3f}".format(R))
                    #1/T = a + b(Ln R) + c(Ln R)^3
                    LnR = math.log(R*1000.0)
                    temp1 = 1/( a + b*LnR + c * ( math.pow( LnR, 3) ) ) - 273.15
                    #print("Temperature T1 {} °C".format(temp1))
                    #temp1 = 1*values[0]
                    temp_avg = temp_avg + temp1
                    n = n + 1
                temp1 = temp_avg/NBR_SAMPLES
                #print("Avg Temp1 {}".format(temp1))
            except Exception as e:
                temp1 = 999.9 
                print("Exception Temperature T1 : " + str(e))
                
            try:
                temp_avg = 0; n=0
                while( n < NBR_SAMPLES ):
                    #print("Start Temperature 2 conversion ADC")
                    values[0] = adc_2.read_adc(1, gain=GAIN_T)
                    #print("NTC Resistor 2 ADC value : {:02.1f}".format(values[0]))
                    R2 = 1.5  # 1.5 KOhm
                    Vin = 3    # 3V Vref
                    vout = (values[0]/2047.0 )*1.024 #4.09
                    #print("Vout : {:02.3f}".format(vout))
                    R = R2 * ( (3.0 / vout) -1)
                    #print("Resistor R : {:02.3f}".format(R))
                    #1/T = a + b(Ln R) + c(Ln R)^3
                    LnR = math.log(R*1000.0)
                    temp2 = 1/( a + b*LnR + c * ( math.pow( LnR, 3) ) ) - 273.15
                    #print("Temperature T2 {} °C".format(temp2))
                    #temp2 = 1*values[0]
                    temp_avg = temp_avg + temp2
                    n = n + 1
                temp2 = temp_avg/NBR_SAMPLES
                #print("Avg Temp2 {}".format(temp2))
            except Exception as e:
                temp2= 999.9 
                print("Exception Temperature T2 : " + str(e)) 
                
            try:
                temp_avg = 0; n=0
                while( n < NBR_SAMPLES ):
                    #print("Start Temperature 2 conversion ADC")
                    values[0] = adc_2.read_adc(2, gain=GAIN_T)
                    #print("NTC Resistor 2 ADC value : {:02.1f}".format(values[0]))
                    R2 = 1.5  # 1.5 KOhm
                    Vin = 3    # 3V Vref
                    vout = (values[0]/2047.0 )*1.024 #4.09
                    #print("Vout : {:02.3f}".format(vout))
                    R = R2 * ( (3.0 / vout) -1)
                    #print("Resistor R : {:02.3f}".format(R))
                    #1/T = a + b(Ln R) + c(Ln R)^3
                    LnR = math.log(R*1000.0)
                    temp3 = 1/( a + b*LnR + c * ( math.pow( LnR, 3) ) ) - 273.15
                    #print("Temperature T3 {} °C".format(temp3))
                    #temp3 = 1*values[0]
                    temp_avg = temp_avg + temp3
                    n = n + 1
                temp3 = temp_avg/NBR_SAMPLES
                #print("Avg Temp3 {}".format(temp3))
            except Exception as e:
                temp3= 999.9 
                print("Exception Temperature T3 : " + str(e)) 
                
            try:
                temp_avg = 0; n=0
                while( n < NBR_SAMPLES ):
                    #print("Start Temperature 2 conversion ADC")
                    values[0] = adc_2.read_adc(3, gain=GAIN_T)
                    #print("NTC Resistor 2 ADC value : {:02.1f}".format(values[0]))
                    R2 = 1.5  # 1.5 KOhm
                    Vin = 3    # 3V Vref
                    vout = (values[0]/2047.0 )*1.024 #4.09
                    #print("Vout : {:02.3f}".format(vout))
                    R = R2 * ( (3.0 / vout) -1)
                    #print("Resistor R : {:02.3f}".format(R))
                    #1/T = a + b(Ln R) + c(Ln R)^3
                    LnR = math.log(R*1000.0)
                    temp4 = 1/( a + b*LnR + c * ( math.pow( LnR, 3) ) ) - 273.15
                    #print("Temperature T4 {} °C".format(temp4))
                    #temp4 = 1*values[0]
                    temp_avg = temp_avg + temp4
                    n = n + 1
                temp4 = temp_avg/NBR_SAMPLES
                #print("Avg Temp4 {}".format(temp4))
            except Exception as e:
                temp4= 999.9 
                print("Exception Temperature T4 : " + str(e)) '''
                
                
            #--------------------------------------------------------------
            # Temperatures - ADC: Address 0x69
            start_time=time.time()
            for i in range(4): 
                try: 
                    temp_avg = 0; n=0
                    while( n < NBR_SAMPLES ):
                        adc_temp[i].convert()
                        ADC_Temp_Steps[i] = adc_temp[i].raw_read()[0]
                        ADC_Temp_Voltages[i] = ADC_LSB * ADC_Temp_Steps[i]
                        vout = ADC_Temp_Voltages[i]
                        R = R53 * ( (VRefTemp / vout) -1)
                        NTC_Resistors[i] = R
                        LnR = math.log(R*1000.0)
                        temp = 1/( a + b*LnR + c * ( math.pow( LnR, 3) ) ) - 273.15
                        temp_avg = temp_avg + temp
                        n = n + 1
                        
                    NTC_Temperatures[i] = temp_avg/NBR_SAMPLES
                    
                except Exception as e:
                    NTC_Temperatures[i] = 999
                    print("ADC Error: {}".format(e))
                    
            print("Resistors: R1: {:05.2f}, R2: {:05.2f}, R3: {:05.2f}, R4: {:05.2f} ".format(NTC_Resistors[0], NTC_Resistors[1], NTC_Resistors[2], NTC_Resistors[3]))
            print("Temperatures: T1: {:05.2f}, T2: {:05.2f}, T3: {:05.2f}, T4: {:05.2f}".format(NTC_Temperatures[0], NTC_Temperatures[1], NTC_Temperatures[2], NTC_Temperatures[3]))
            print("Voltages: V1: {:05.2f}, V2: {:05.2f}, V3: {:05.2f}, V4: {:05.2f}".format(ADC_Temp_Voltages[0], ADC_Temp_Voltages[1], ADC_Temp_Voltages[2], ADC_Temp_Voltages[3]))
            print("Steps: Input1: {}, Input2: {}, Input3: {}, Input4: {}".format(ADC_Temp_Steps[0], ADC_Temp_Steps[1], ADC_Temp_Steps[2], ADC_Temp_Steps[3]))
            print(time.time()-start_time)
            print("")
                
                

            # Set the global shared variables
            # Temperature
            for i in range(4): 
                TempPress[i] = float("{:03.1f}".format(NTC_Temperatures[i])) 
            
            '''TempPress[0] = float("{:03.1f}".format(temp1)) #temp1
            TempPress[1] = float("{:03.1f}".format(temp2)) #temp2
            TempPress[2] = float("{:03.1f}".format(temp3)) #temp13
            TempPress[3] = float("{:03.1f}".format(temp4)) #temp4'''
            
            # Pressure
            for j in range(4,7):
                TempPress[j] = float("{:03.1f}".format(WNK83MA_Pressure[j-4])) 
            '''TempPress[4] = float("{:03.1f}".format(press1)) #press1
            TempPress[5] = float("{:03.1f}".format(press2)) #press2
            TempPress[6] = float("{:03.1f}".format(press3)) #press3'''
            
            TempPress[7] = float("{:03.1f}".format(POWER[0])) #press4
            #print('Temp1: {:05.2f}, Temp2:{:05.2f}, Press1:{:05.2f}'.format(temp1, temp2, press1)  )
            #print('\nTemp1: {:05.2f}, Temp2:{:05.2f}, Temp3:{:05.2f}, Temp4:{:05.2f}'.format(temp1, temp2, temp3, temp4)  )
            #print('Press1:{:05.2f}, Press2:{:05.2f}, Press3:{:05.2f}, Press4:{:05.2f}'.format(press1, press2, press3, press4)  )
            
            ttpp_logger.info('Temp1: {:05.2f}, Temp2:{:05.2f}, Temp3:{:05.2f}, Temp4:{:05.2f}'.format(NTC_Temperatures[0], NTC_Temperatures[1], NTC_Temperatures[2], NTC_Temperatures[3])  )
            ttpp_logger.info('Press1:{:05.2f}, Press2:{:05.2f}, Press3:{:05.2f}, Power:{:05.2f}'.format(WNK83MA_Pressure[0], WNK83MA_Pressure[1], WNK83MA_Pressure[2], POWER[0])  )
            print("=====================================================\n")
                
            #
            time.sleep(1)

        except Exception as e:
            print("Exception : " + str(e))
            tpp_logger.error("Exception {}".format( str(e) ) )
            print(e)
        
# ----------------------------------------------------------------------------


def main():
    
    # Init/set the global temperature and pressure variables to 0
    TempPress[0]=0.0; TempPress[1]=0.0; TempPress[2]=0.0; TempPress[3] = 0.0
    TempPress[4]=0.0; TempPress[5]=0.0; TempPress[6]=0.0; TempPress[7] = 0.0
    TempPress[8]=0
    # Start the Independent Temperature and Pressure measurement process
    try:
        global TempPressPow_Process
        TempPressPow_Process = Process( target=tempPressPowerMethod, args=(CLS_Drinko_DEVICE.POWER_SENSOR,) )
        TempPressPow_Process.start()
        #print("Independent Process Temperature and Pressure started ..")
        ttpp_logger.info("[+] Process Temperature, Pressure and Power started ..")
    except Exception as e:
        ttpp_logger.error("[-] Error Process Temp, Press, and Power: {}".format(e) )
    
    



if __name__ == "__main__":
    main()
    





