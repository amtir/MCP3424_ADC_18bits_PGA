#!/usr/bin/python3

'''
    MCP3424 ADC 18bits with PGA
    DROKOTEC
    A M.
    25-11-2022

'''

import glob
import time, math
import logging
import smbus
from MCP342x import MCP342x


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
WNK83MA_Pressure = [0,0,0,0]
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
NTC_Temperatures = [0,0,0,0]
#----------------------------------------------------------------------



def main():
    
    while(True):
        
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
                print("ADC Error: {}".format(e))
                
        print("Resistors: R1: {:05.2f}, R2: {:05.2f}, R3: {:05.2f}, R4: {:05.2f} ".format(NTC_Resistors[0], NTC_Resistors[1], NTC_Resistors[2], NTC_Resistors[3]))
        print("Temperatures: T1: {:05.2f}, T2: {:05.2f}, T3: {:05.2f}, T4: {:05.2f}".format(NTC_Temperatures[0], NTC_Temperatures[1], NTC_Temperatures[2], NTC_Temperatures[3]))
        print("Voltages: V1: {:05.2f}, V2: {:05.2f}, V3: {:05.2f}, V4: {:05.2f}".format(ADC_Temp_Voltages[0], ADC_Temp_Voltages[1], ADC_Temp_Voltages[2], ADC_Temp_Voltages[3]))
        print("Steps: Input1: {}, Input2: {}, Input3: {}, Input4: {}".format(ADC_Temp_Steps[0], ADC_Temp_Steps[1], ADC_Temp_Steps[2], ADC_Temp_Steps[3]))
        print(time.time()-start_time)
        print("")
        
        
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
                print("Exception Pressure P{} : {} ".format(i,e))
            
        print("Pressures: P1: {:05.2f}, P2: {:05.2f}, P3: {:05.2f}".format(WNK83MA_Pressure[0], WNK83MA_Pressure[1], WNK83MA_Pressure[2],))
        print("Voltages: V1: {:05.2f}, V2: {:05.2f}, V3: {:05.2f}".format(ADC_Press_Voltages[0], ADC_Press_Voltages[1], ADC_Press_Voltages[2]))
        print("Steps: Input1: {}, Input2: {}, Input3: {}".format(ADC_Press_Steps[0], ADC_Press_Steps[1], ADC_Press_Steps[2]))
        print(time.time()-start_time)
        print()
        
        
        #--------------------------------------------------------------
        # Power sensor, Power consumption
        MAX_V = 0.0
        VOLT_TO_AMP = 30
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
            power4 = P
            #print(P)
                
            print("Max V: {}".format(MAX_V))
            print("V_RMS V: {}".format(V_RMS))
            print("Power: {}".format(P))
            print(time.time()-start_time)
            print("-----------------\n")
                
        except Exception as e:
            print("Exception Power P4: ".format(e) )
        
        
        
if __name__ == "__main__":
    main()
    
