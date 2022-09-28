#!/usr/bin/python3

'''
    MCP3424 ADC 18bits with PGA
    DROKOTEC
    A M.
    28-09-2022

'''

import glob
import time
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

print("\n MCP3424 ADC initialisation:")

# Create objects for each signal to be sampled
addr68_ch0 = MCP342x(bus, 0x68, channel=0, resolution=18, gain=1)
addr68_ch1 = MCP342x(bus, 0x68, channel=1, resolution=18, gain=1)
addr68_ch2 = MCP342x(bus, 0x68, channel=2, resolution=18, gain=1)
addr68_ch3 = MCP342x(bus, 0x68, channel=3, resolution=18, gain=1)

addr6a_ch0 = MCP342x(bus, 0x6a, channel=0, resolution=18, gain=1)
addr6a_ch1 = MCP342x(bus, 0x6a, channel=1, resolution=18, gain=1)
addr6a_ch2 = MCP342x(bus, 0x6a, channel=2, resolution=18, gain=1)
addr6a_ch3 = MCP342x(bus, 0x6a, channel=3, resolution=18, gain=1)

adc_chs = [addr6a_ch0, addr6a_ch1, addr6a_ch2, addr6a_ch3 ] #, addr6a_ch0, addr6a_ch1, addr6a_ch2, addr6a_ch3]
print(adc_chs)
adc2_chs = [addr68_ch0, addr68_ch1, addr68_ch2, addr68_ch3 ] #, addr6a_ch0, addr6a_ch1, addr6a_ch2, addr6a_ch3]
print(adc2_chs)
print("\n")


# Half full-range 17 bits :    131071 Steps    0x1FFFF   --> 17bits

# Voltage and steps
MAX_VOLTAGE_OUT = 5.20  # [V]
MAX_STEPS = 131071      # Steps
MAX_VOLTAGE_IN = 2.12   # [V]

# Resistors
R1=10                   # KOhm
R2=6.8                  # KOhm 

# Coefficient and Constant
K=(R1+R2)/R2
K1 = MAX_VOLTAGE_OUT / MAX_VOLTAGE_IN
K2 = MAX_VOLTAGE_OUT / MAX_STEPS


ADC_Steps = [0,0,0,0]; ADC2_Steps = [0,0,0,0]
ADC_Voltages = [0,0,0,0]; ADC2_Voltages = [0,0,0,0]


while(True):
    # ADC 1: Address 0x6A
    for i in range(4): 
        #print("{} : Resolution: {} bits".format( i, adc_chs[i].get_resolution()) )
        adc_chs[i].convert()
        ADC_Steps[i] = adc_chs[i].raw_read()[0]
        ADC_Voltages[i] = (MAX_VOLTAGE_OUT / MAX_STEPS) * ADC_Steps[i]
        
    #print("ADC1 Steps: {} {} {} {}  [Steps]".format( ADC_Steps[0],  ADC_Steps[1],  ADC_Steps[2],  ADC_Steps[3]) ) 
    print("ADC1 Voltages output: {:2.2f} {:2.2f} {:2.2f} {:2.2f}  [V]".format( ADC_Voltages[0],  ADC_Voltages[1],  ADC_Voltages[2],  ADC_Voltages[3]) ) 
    
    # ADC 2: Address 0x68
    for i in range(4): 
        #print("{} : Resolution: {} bits".format( i, adc_chs[i].get_resolution()) )
        adc2_chs[i].convert()
        ADC2_Steps[i] = adc2_chs[i].raw_read()[0]
        ADC2_Voltages[i] = (MAX_VOLTAGE_OUT / MAX_STEPS) * ADC2_Steps[i]
        
    #print("ADC2 Steps: {} {} {} {}  [Steps]".format( ADC2_Steps[0],  ADC2_Steps[1],  ADC2_Steps[2],  ADC2_Steps[3]) ) 
    print("ADC2 Voltages output: {:2.2f} {:2.2f} {:2.2f} {:2.2f}  [V]".format( ADC2_Voltages[0],  ADC2_Voltages[1],  ADC2_Voltages[2],  ADC2_Voltages[3]) ) 
    
    print("-----------------\n")
    time.sleep(1)
