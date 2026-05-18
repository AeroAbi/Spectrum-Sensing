

import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import time


class KeysightOcilloScope:
    def __init__(self, ip_address):
        self.ip = ip_address
        self.rm = None
        self.scope = None

   
    def connect(self):
        self.rm = pyvisa.ResourceManager()
        resource = f"TCPIP0::{self.ip}::inst0::INSTR"
        self.scope = self.rm.open_resource(resource)

        self.scope.timeout = 5000
        self.scope.write_termination = '\n'
        self.scope.read_termination = '\n'

        print(f"Connected to: {self.ip}")
        print(self.scope.query("*IDN?"))

   
    def configure_oscilloscope(self,channel=1,volts_per_div=0.1,time_per_div=100e-6):   #100 mV/div, 20 ns/div, 50 mV.

        self.scope.write(f":CHAN{channel}:DISP ON")
        self.scope.write(f":CHAN{channel}:SCAL {volts_per_div}")
        self.scope.write(f":TIM:SCAL {time_per_div}")

        print("Waveform Parameters uploaded")


    def trigger_configure(self, channel=2,trigger_level = 100e-3):
        self.scope.write(":TRIG:SWE TRIG") #CHANGING TRIGGER SETUP TO TIGERED 
        self.scope.write(":TRIG:MODE EDGE")  #edge trigger.
        self.scope.write(f":TRIG:EDGE:SOUR CHAN{channel}")
        self.scope.write(f":TRIG:EDGE:LEV {trigger_level}")

        print("Trigger settings uploaded.")


    def acquire_data(self, channel=1):  #getCurrentWaveform(dev,channelNumber) getWaveformSingleTrigger(dev,channelNumber)

        # Single acquisition
        self.scope.write(":SING")
        timeout_ms = 500 #21 millisecs
        start_time = time.time()
        

        while True:
            try:
                opc = self.scope.query("*OPC?")

                if opc == '1':
                    print("Waveform Acquisition completed.")
                    break
                    
                 # while int(self.scope.query("*OPC?")) != 1:
        #     continue
        

            except Exception as e:
                print(f"OPC Error: {e}")
                elapsed_ms = (time.time() - start_time) * 1000
                print(f"Elapsed time: {elapsed_ms:.3f}ms") 
                if elapsed_ms > timeout_ms:
                    print("Timeout reached.")
                    return None             
                print(f"Continuing...")
                continue

            # elapsed_ms = (time.time() - start_time) * 1000
            # print(f"Elapsed time: {elapsed_ms}")

       
        self.scope.write(f":WAV:SOUR CHAN{channel}")  #select source
        self.scope.write(":WAV:FORM WORD")

        raw = self.scope.query_binary_values( ":WAV:DATA?", datatype='H',container=np.array) #read
        data = np.savetxt("data.txt",raw,fmt='%.2f')
        print("Waveform acquired.")

        stop_time = time.time()
        total_time = (stop_time-start_time) * 1e3
        print(f"Total Time taken: {total_time:.3f} ms")
        return raw

    def close(self):
        self.scope.close()
        self.rm.close()
        print("Connection closed.")

#   ##test plotting 
#     def plot_data(self, data):

#         plt.figure(figsize=(10, 4))
#         plt.plot(data)
#         plt.title("Acquired Waveform")
#         plt.xlabel("Samples")
#         plt.ylabel("Amplitude")
#         plt.grid(True)
#         plt.show()


  #main
if __name__ == "__main__":

    scope = KeysightOcilloScope("192.168.0.123")   
    scope.connect()
    scope.configure_oscilloscope()
    scope.trigger_configure()
    data = scope.acquire_data(channel=1)
    # scope.plot_data(data)
    scope.close()