
import ctypes as ct
import numpy as np
import csv
import sys
import os
from modules.example_helpers import *  # Assuming this helper exists as in original
import matplotlib.pyplot as plt 
from logger import awg_logger
sys.path.insert(1, os.path.dirname(os.path.realpath(__file__))+'/..')
print(os.path.dirname(os.path.realpath(__file__))+'/..')
ADQAPI2 = adqapi_load()
SW_TRIG = 1
EXT_TRIG = 2
TRIG_THRESHOLD = 0.020  #if external trigger applied. Trigger threshold should be less then the external trigger in our case it is 50mV
HIGH_IMPEDANCE = 1  
LOW_IMPEDANCE = 0
LVL_FALLING = 0
LVL_RISING = 1

class ADQ14Reader:

    
    def __init__(self, device_num=1, samples_per_record=110, number_of_records=1, triggerdelay=0, trigtype=SW_TRIG):
        """
        Initialize ADQ14 reader.
        device_num: ADQ device index (1-based)
        samples_per_record: Samples per acquisition record
        number_of_records: Number of records to acquire
        """
        self.ADQAPI = ADQAPI2
        self.adqcu = ct.c_void_p(self.ADQAPI.CreateADQControlUnit())
        self.device_num = device_num   # Convert to 0-based
        self.samples_per_record = samples_per_record
        self.number_of_records = number_of_records
        self.nof_channels = 4
        self.triggerdelay = triggerdelay
        self.trigtype = trigtype
        self.channel_mask = 0xFF  # All channels A,B,C,D
        self._setup_device()
        self.logger = awg_logger("ADQ14")
        
    
    def _setup_device(self):
        """Setup device connection, clock, and trigger as in original code."""
        self.ADQAPI.ADQControlUnit_EnableErrorTrace(self.adqcu, 65536, '.')
        self.ADQAPI.ADQControlUnit_FindDevices(self.adqcu)
        nofADQ = self.ADQAPI.ADQControlUnit_NofADQ(self.adqcu)
        if nofADQ <= 0:
            raise RuntimeError("No ADQ devices found")
        
        # Select device
        
        print(f"Found {nofADQ} ADQ devices")
        
        # Clock and test pattern
        ADQ_CLOCK_INT_EXTREF = 0
        ADQAPI2.ADQ_SetClockSource(self.adqcu, self.device_num, ADQ_CLOCK_INT_EXTREF)
        self.ADQAPI.ADQ_SetTestPatternMode(self.adqcu, self.device_num, 0)
        
        # External trigger setup (EXTTRIG1, rising edge, high impedance)
        self.trigtype = SW_TRIG 
        if self.trigtype==SW_TRIG:
            success=ADQAPI2.ADQ_SetTriggerMode(self.adqcu, self.device_num, self.trigtype)
            if (success == 0):
                 print('ADQ_SetTriggerMode success')
        if self.trigtype == EXT_TRIG:
            success = ADQAPI2.ADQ_SetTriggerMode(self.adqcu, self.device_num, self.trigtype)   #setting the external trigger mode.
            if (success == 0):
                print('ADQ_SetTriggerMode failed.')
            print("......External Trigger applied......")
            success = ADQAPI2.ADQ_SetTriggerInputImpedance(self.adqcu, self.device_num,1,HIGH_IMPEDANCE)   #Set to 1 for TRIG connector and 2 for SYNC connector
            if (success == 0):
                print('ADQ_SetTriggerInputImpedance failed.')
            success = ADQAPI2.ADQ_SetExternTrigEdge(self.adqcu, self.device_num,LVL_RISING)  # Rising: 1, Falling: 0, both: 2 (for ADQ14 only)
            if (success == 0):
                print('ADQ_SetExternTrigEdge failed.')
            success = ADQAPI2.ADQ_SetExternalTriggerDelay(self.adqcu, self.device_num,self.triggerdelay)
            if (success == 0):
                print('ADQ_SetExternalTriggerDelay failed.')

            # changing the external trigger threshold
            success = ADQAPI2.ADQ_SetExtTrigThreshold(self.adqcu, self.device_num,1,ct.c_double(TRIG_THRESHOLD))
            if (success == 0):
                print('ADQ_SetExtTrigThreshold failed.')
            result=ct.c_uint(0)
            ADQAPI2.ADQ_GetExternTrigEdge(self.adqcu, self.device_num,ct.pointer(result))
            if(result.value==1):
                print("....External trig edge rising edge....")

            ADQAPI2.ADQ_GetTriggerInputImpedance(self.adqcu, self.device_num,1,ct.pointer(result))
            if(result.value==1):
                print("....External trig is at HIGH Impedance....")

        #self.ADQAPI.ADQ_SetTriggerInputImpedance(self.adqcu, self.device_num, 1, 1)  # High Z
        # self.ADQAPI.ADQ_SetExternTrigEdge(self.adqcu, self.device_num, 1)  # Rising
        # self.ADQAPI.ADQ_SetExternalTriggerDelay(self.adqcu, self.device_num, 0)
        # self.ADQAPI.ADQ_SetExtTrigThreshold(self.adqcu, self.device_num, 1, ct.c_double(0.020))
        
        self.nof_channels = self.ADQAPI.ADQ_GetNofChannels(self.adqcu, self.device_num)
        print(f"Device {self.device_num} ready with {self.nof_channels} channels")
    
    
    def set_params(self, channel_mask, samples_per_record, number_of_records):
        self.channel_mask = channel_mask
        self.samples_per_record = samples_per_record
        self.number_of_records = number_of_records
    
    def save_to_csv(self, data,fname):
        with open(fname, 'w', newline='') as f:
            writer = csv.writer(f)   
            writer.writerow(data)

   
    def acquire_reading(self):
        """
        Take one reading: setup multi-record, arm trigger, wait for external trigger,
        return raw data as (records, samples, channels) shaped array.
        """
    
        # Multi-record setup
        self.ADQAPI.ADQ_SetSampleSkip(self.adqcu, self.device_num, 1)
        self.ADQAPI.ADQ_SetPreTrigSamples(self.adqcu, self.device_num, 0)
        self.ADQAPI.ADQ_SetTriggerDelay(self.adqcu, self.device_num, self.triggerdelay)
        self.ADQAPI.ADQ_MultiRecordSetChannelMask(self.adqcu, self.device_num, self.channel_mask)
        self.ADQAPI.ADQ_MultiRecordSetup(self.adqcu, self.device_num, self.number_of_records, 
                                       self.samples_per_record)
        self.nof_channels = self.ADQAPI.ADQ_GetNofChannels(self.adqcu, self.device_num)
        print(f"Device {self.device_num} ready with {self.nof_channels} channels")
    
        # Arm trigger
        self.ADQAPI.ADQ_DisarmTrigger(self.adqcu, self.device_num)
        self.ADQAPI.ADQ_ArmTrigger(self.adqcu, self.device_num)
        print("Device armed - apply external trigger")
        
        # Allocate buffers
        target_buffers = (ct.POINTER(ct.c_int16*(self.number_of_records*self.samples_per_record)) * self.nof_channels)()
        for bufp in target_buffers:
            bufp.contents = (ct.c_int16 * (self.number_of_records * self.samples_per_record))()
    # Assumes defined in examplehelpers
        target_headers = (HEADER * self.number_of_records)()
        target_headers_vp = ct.cast(ct.pointer(target_headers), ct.POINTER(ct.c_void_p))
        
        for trig in range(self.number_of_records):
            self.ADQAPI.ADQ_SWTrig(self.adqcu, self.device_num)
        # Wait for data (non-blocking, checks records)
        records_completed = 0
        records_available =0
        while records_completed < self.number_of_records:
            records_available = self.ADQAPI.ADQ_GetAcquiredRecords(self.adqcu, self.device_num)
            # print(records_available)
            #print(records_completed)

            new_records = records_available - records_completed
            if new_records > 0:
                status = self.ADQAPI.ADQ_GetDataWHTS(
                    self.adqcu, self.device_num, target_buffers, target_headers, None,
                    self.number_of_records * self.samples_per_record, 2, records_completed,
                    new_records, self.channel_mask, 0, self.samples_per_record, 0x00
                )
                print(status)
                if status == 0:
                    self.ADQAPI.DeleteADQControlUnit(self.adqcu)
                    sys.exit()
                    raise RuntimeError(f"ADQGetDataWHTS failed with status {status}")
                    
                # Reorganize into numpy array: (records, samples, channels)
                data = [np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16),
                    np.zeros(self.number_of_records*self.samples_per_record, dtype=np.int16)]
                print(new_records,self.samples_per_record,records_completed)
                for ch in range(self.nof_channels):
                    databuf = np.frombuffer(target_buffers[ch].contents, dtype=np.int16, 
                                        count=self.samples_per_record * new_records)
                    for rec in range(0,new_records):
                        for s in range(0,self.samples_per_record):
                            data[ch][(records_completed+rec)*self.samples_per_record + s] = databuf[rec*self.samples_per_record + s]
                        print(rec*self.samples_per_record + s)
                records_completed += new_records
                #target_headers_vp.contents.value += new_records*ct.sizeof(HEADER)
                
        print('Records read out:',records_completed)
        self.ADQAPI.ADQ_MultiRecordClose(self.adqcu, self.device_num)
        # self.save_to_csv(data[3],'test.csv')
        return data
    

    def acquire_voltage_reading(self):
        """Acquire and convert to voltage using 1.9V range and 16-bit ADC."""
        raw_data = self.acquire_reading()
        voltage_data = np.empty_like(raw_data)
        for i in range(4):
            voltage_data[i] = np.float32(raw_data[i] * 1.92 / 2**15)  # Convert to voltage
            print(type(voltage_data[i].astype(np.float32).tolist()))
        return voltage_data
    
    
    def close(self):
        """Cleanup."""
        if self.adqcu:
            self.ADQAPI.DeleteADQControlUnit(self.adqcu)


if __name__ == "__main__":
    reader = ADQ14Reader(samples_per_record=1024, number_of_records=1)
    try:
        data = reader.acquire_reading()   
        print(data[:20])
        
        y = (data[3]/2**15)*(1.9/2)
        plt.plot(y.T, '.-')
        plt.xlabel("Sample index")
        plt.ylabel("Amplitude (ADC counts)")
        plt.title("ADQ14 waveform - Record 0, Channel 0")
        plt.grid(True)
        plt.show()
    finally:
        reader.close()

