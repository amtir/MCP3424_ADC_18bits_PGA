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
    
   
    while True: # infinite loop
        try:
            
            temp1 = 999.9; temp2 = 999.9; temp3 = 999.9; temp4 = 999.9;
            press1 = 999.9; press2 = 999.9; press3 = 999.9; press4 = 999.9; power4 = 999.9;
            
            #--------------------------------------------------------------------------------------
            # Read Pressure P1, P2, P3, Pow4 (Sensor Pressure transmitter 10 Bar, WNK83MA ADC18bits).
            
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
            
            # Pressure
            for j in range(4,7):
                TempPress[j] = float("{:03.1f}".format(WNK83MA_Pressure[j-4])) 
            
            TempPress[7] = float("{:03.1f}".format(POWER[0])) 
            
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
        TempPressPow_Process = Process( target=tempPressPowerMethod )
        TempPressPow_Process.start()
        #print("Independent Process Temperature and Pressure started ..")
        ttpp_logger.info("[+] Process Temperature, Pressure and Power started ..")
    except Exception as e:
        ttpp_logger.error("[-] Error Process Temp, Press, and Power: {}".format(e) )
    
    



if __name__ == "__main__":
    main()
    





