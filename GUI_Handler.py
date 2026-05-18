import glob
import os
import time
from datetime import datetime
import threading
import base64

import math
import csv
from unittest import case
from unittest import case
from scipy import signal
import numpy as np
from numpy.fft import fft, fftshift, fftfreq

from TektronixAWG import TektronixAWG
# from AWG_Controller import AWG_Controller
# from WaveformGenerator import WaveformGenerator
from WaveformGenerator_v2 import WaveformGenerator
from CombinedWaveformGenerator import CombinedWaveformGenerator
from ADQ14 import ADQ14Reader
from logger import awg_logger
from progress_bar import ProgressBox #add

from PyQt5.QtCore import QThread
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFormLayout
from matplotlib.figure import Figure

class GUI_Handler:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.awg = None
        self.adq = None
        self.generator = WaveformGenerator()  # For single waveforms
        self.combined_gen=CombinedWaveformGenerator()
        self.logger = awg_logger("Handler")
        self.remote_path = "C:\\Users\\Public\\Documents\\"
        self.folder_name = "C:\\Users\\USER\\Desktop\\Abinaya\\tmp\\"


    def handle_generate_waveform2(self):
        waveform = self.gui.params["waveform"]["type"]
        params = self.gui.params["waveform"]["params"]
        amp_params = self.gui.params["amplitude"]["params"]
        amps = np.arange(float(amp_params["start_amp"]), float(amp_params["stop_amp"]) + 0.00001, float(amp_params["step_amp"]))
        self.generator.sampling_frequency = self.gui.params["sampling_freq"]
        self.gui.awg_fig.clear()
        ax1 = self.gui.awg_fig.add_subplot(2, 1, 1)
        ax2 = self.gui.awg_fig.add_subplot(2, 1, 2)
        set_params = params.copy() # passing dict and wftype to generator to make it modular
        # TODO: remove th switch case and somehow make the generation of the sweep modular

        match waveform:
            case "Sine":
                freqs = np.arange(float(params["start_freq"]), float(params["stop_freq"]) + 0.00001, float(params["step_freq"]))
                set_params.pop("start_freq")
                set_params.pop("stop_freq")
                set_params.pop("step_freq")
                for f in freqs:
                    set_params["frequency"] = f
                    w = self.generator.generate_with_params(wftype=waveform, params=set_params, duration_s=self.gui.params["signal_duration"])
                    t = self.generator._build_time_axis(duration_s=self.gui.params["signal_duration"])
                    self.plot_waveform_and_spectrum(t, w, self.gui.awg_fig, self.gui.awg_canvas, ax1, ax2, self.gui.params["sampling_freq"], "FFT")
            case "LFM":
                center_freqs = np.arange(float(params["start_center_frequency"]), float(params["stop_center_frequency"]) + 0.00001, float(params["step_center_frequency"]))
                set_params.pop("start_center_frequency")
                set_params.pop("stop_center_frequency")
                set_params.pop("step_center_frequency")
                for cf in center_freqs:
                    set_params["center_frequency"] = cf
                    w = self.generator.generate_with_params(wftype=waveform, params=set_params, duration_s=self.gui.params["signal_duration"])
                    t = self.generator._build_time_axis(duration_s=self.gui.params["signal_duration"])
                    self.plot_waveform_and_spectrum(t, w, self.gui.awg_fig, self.gui.awg_canvas, ax1, ax2, self.gui.params["sampling_freq"], "FFT")
            
            case "StepLFM": ##updated##   
                start_freqs = np.arange(float(params["Start_frequency_initial"]), float(params["Start_frequency_final"]) + 0.0001, float(params["Start_frequency_step"]))
                print("Start Frequency Sweep Values (GHz):", start_freqs)
                # StepLFM_Nstep = 5     ##testing
                # StepLFM_stepfreq_hz = 1 *1e9
                # for step, fstart_current in enumerate(start_freqs):
                #     fstop_current = fstart_current + (StepLFM_Nstep - 1)*StepLFM_stepfreq_hz
                #     print(f"Sweep {step+1}: Start {fstart_current/1e9:.2f} GHz, Stop {fstop_current/1e9:.2f} GHz")
                set_params.pop("Start_frequency_initial")
                set_params.pop("Start_frequency_final")
                set_params.pop("Start_frequency_step")
                # #StepLFM
                # set_params.pop("StepLFM_frequency")
                # set_params.pop("StepLFM_Nstep")   
  
                for sf in start_freqs:
                    set_params["Start_Frequency"] = sf
                    w = self.generator.generate_with_params(wftype=waveform, params=set_params, duration_s=self.gui.params["signal_duration"])
                    t = self.generator._build_time_axis(duration_s=self.gui.params["signal_duration"])
                    self.plot_waveform_and_spectrum(t, w, self.gui.awg_fig, self.gui.awg_canvas, ax1, ax2, self.gui.params["sampling_freq"], "FFT")
    
    
    def plot_waveform_and_fft(self, t, w, fig, canvas, ax1, ax2, sampling_frequency):
        # compute FFT using existing method
        print(f"Calculating FFT with sampling frequency: {sampling_frequency} Hz")
        freq, mag = self.fft_signal(w, sampling_frequency)
        ax1.plot(t * 1e9, w)
        ax1.set_xlabel("Time (ns)")
        ax1.set_ylabel("Amplitude (V)")
        ax1.grid(True)
        
        ax2.plot(freq, mag)
        ax2.set_xlabel("F (GHz)")
        ax2.set_ylabel("Power (dBm)")
        ax2.grid(True)
        fig.tight_layout()
        canvas.draw()

    def plot_waveform_and_spectrum(self, t, w, fig, canvas,ax1, ax2, fs, spectype = "FFT"):
        ax1.plot(t * 1e9, w)
        ax1.set_xlabel("Time (ns)")
        ax1.set_ylabel("Amplitude (V)")
        ax1.grid(True)
        if spectype == 'FFT':
            freq, mag = self.generator.compute_fft(w=w, sampling_frequency=fs)
            ax2.plot(freq, mag)
            ax2.set_xlabel("F (GHz)")
            ax2.set_ylabel("Power (dBm)")
            # ax2.set_xlim(0,max(freq))
            ax2.grid(True)
        elif spectype == 'Spect':
            f_spec, t_spec, Sxx_bin_dBm = self.generator.compute_spectrogram(data=w, sampling_frequency=fs)
            im = ax2.pcolormesh(t_spec*1e9, f_spec/1e6, Sxx_bin_dBm, shading='gouraud')
            vmax = np.max(Sxx_bin_dBm)    #ar
            vmin = vmax - 10  # show 10 dB dynamic range
            im.set_clim(vmin, vmax)
            cbar = self.gui.adqfig.colorbar(im, ax=ax2) #ar
            cbar.set_label('Power [dBm]')
            ax2.set_ylabel('Freq [MHz]')
            ax2.set_xlabel('Time [ns]')
        fig.tight_layout()
        canvas.draw()

    def create_adq_csv(self, waveform_type, parameters):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        base_path = self.gui.params["data_save_location"]

        csv_file = os.path.join(base_path, f"SS_{waveform_type}_{timestamp}.csv")

        fcsv = open(csv_file, 'w', newline='')
        writer = csv.writer(fcsv)

        # Header (written once)
        # Use parameter keys as columns, plus Data and Reference
        param_headers = list(parameters.keys())
        writer.writerow(param_headers + ['Amplitude', 'Data', 'Reference'])

        print(f"Created file at : {csv_file}")

        return fcsv, writer, csv_file
    
    #add
    def sweep_with_progressbar(self, sweep_values, waveform, label_prefix = "Generating Waveforms...."):
        progress = ProgressBox(label_prefix, len(sweep_values), self.gui)
        progress.show()

        step_count = 0
        for value in sweep_values:         
            step_count += 1
            time.sleep(1)
            if progress.wasCanceled():
                print(f"{waveform} generation cancelled by user")
                return False
        progress.close()
#                    

    def run(self):
        self.gui.log_box.append(f"channel running started")
        if self.awg == None:
            QMessageBox.warning(self.gui, "Warning", "Connect to AWG first!!")
            return
        # print(self.gui.params)

        channel = self.gui.params["channel"]
        amplitude_dict = self.gui.params["amplitude"]["params"]
        amps = np.arange(float(amplitude_dict["start_amp"]), float(amplitude_dict["stop_amp"]) + 0.00001, float(amplitude_dict["step_amp"]))

        self.gui.log_box.append(f"Remote path: {self.remote_path}")
        # remote_path = os.path.join(self.remote_path, self.folder_name).replace("\\", "/")
        remote_path = self.remote_path
        waveform = self.gui.params["waveform"]["type"]
        params = self.gui.params["waveform"]["params"]

        match waveform:
            case "Sine":
                freqs = np.arange(float(params["start_freq"]), float(params["stop_freq"]) + float(params["step_freq"]), float(params["step_freq"]))
                set_params = params.copy()
                set_params.pop("start_freq")
                set_params.pop("stop_freq")
                set_params.pop("step_freq")
                set_params["frequency"] = None
                fcsv, writer, csv_file = self.create_adq_csv(waveform_type=waveform, parameters=set_params)
                #add
                #progress =ProgressBox("Generating Sine waveforms...", len(freqs, self.gui))
                
                for f in freqs:
                    set_params["frequency"] = f
                    self.sendWaveform(channel=channel, waveform=waveform, set_params=set_params, amps=amps, writer=writer)
                self.sweep_with_progressbar(sweep_values =freqs, waveform = waveform, label_prefix = "Generating Sine Waveforms....") #add  - check the sweep count and visualization 
                  ##or add the progress in the terminal
                  ##check - if i can call the class directly or call it in a fn

                #     for chtype, chno in channel.items():
                #         print(set_params)
                #         w = self.generator.generate_with_params(wftype=waveform, params=set_params, duration_s=self.gui.params["signal_duration"])
                #         # t, w = self.generator.sinusoidal(frequency=f, sampling_freq=self.gui.params["sampling_freq"])
                #         self.save_waveform_to_csv(w_values=w, channel=chtype, folder=self.folder_name)
                #         self.gui.log_box.append(f"Generated {waveform} waveform for channel {chtype} with frequency {f} GHz")
                #         local = self.folder_name+chtype+".csv"
                #         awgFile = self.remote_path+chtype+".csv"
                #         self.awg.transfer_waveform(LOCAL_FILE=local , AWG_FILE=awgFile)
                #         self.awg.import_file(channel=chno,filename= awgFile)
                #     for amp in amps:
                #         for chtype, chno in channel.items():
                #             self.awg.set_output_voltage_custom(chno, amp)
                #             self.gui.log_box.append(f"Set amplitude {amp} V for channel {chtype}")
                #             self.awg.set_output_state(chno, 1)
                #         self.awg.initiate_signal()
                #         print("Waiting for signal to generate...")
                #         # time.sleep(self.gui.params['awg_delay'])
                #         time.sleep(1)
                #         print("Read data")
                #         # adq_data = self.adq.acquire_voltage_reading()
                #         adq_data = self.adq.acquire_reading()
                #         data = (adq_data[self.gui.params['adq_channel']['params']['data']]* 1.92 / 2**15).tolist()
                #         ref = (adq_data[self.gui.params['adq_channel']['params']['reference']]* 1.92 / 2**15).tolist()
                #         print("element type", type(data[1]))
                #         print("Datatype:",type(data))
                #         print("Length:", len(data))
                #         self.awg.abort_wave_generation()
                #         # writer.writerow([f, amp, adq_data[self.gui.params['adq_channel']['params']['data']].tolist(), adq_data[self.gui.params['adq_channel']['params']['reference']].tolist()])
                #         writer.writerow([f, amp, data, ref])
                #         print("saved")
            case "LFM":
                center_freqs = np.arange(float(params["start_center_frequency"]), float(params["stop_center_frequency"]) + 0.0001, float(params["step_center_frequency"]))
                print("Center frequency sweep :",center_freqs)
                set_params = params.copy()
                set_params.pop("start_center_frequency")
                set_params.pop("stop_center_frequency")
                set_params.pop("step_center_frequency")
                set_params["center_frequency"] = None
                fcsv, writer, csv_file = self.create_adq_csv(waveform_type=waveform, parameters=set_params)
                for cf in center_freqs:
                    set_params["center_frequency"] = cf
                    self.sendWaveform(channel=channel, waveform=waveform, set_params=set_params, amps=amps, writer=writer)
                #add
                # progress = ProgressBox("Generating LFM Waveforms...", len(center_freqs), self.gui)
                self.sweep_with_progressbar(sweep_values=center_freqs, waveform = waveform, lebel_prefix ="Generating LFM Waveform...")    
            
            case "StepLFM":  ##updated##

                start_freqs = np.arange(float(params["Start_frequency_initial"]), float(params["Start_frequency_final"]) + 0.0001, float(params["Start_frequency_step"]))
               
                set_params = params.copy()
                set_params.pop("Start_frequency_initial")
                set_params.pop("Start_frequency_final")
                set_params.pop("Start_frequency_step")
                set_params["Start_Frequency"] = None 
                # #StepLFM
                fcsv, writer, csv_file = self.create_adq_csv(waveform_type=waveform, parameters=set_params)
                for sf in start_freqs:
                    set_params["Start_Frequency"] = sf
                    self.sendWaveform(channel=channel, waveform=waveform, set_params=set_params, amps=amps, writer=writer)   
                
                #add
                self.sweep_with_progressbar(sweep_values = start_freqs, waveform = waveform, label_prefix = "Generating StepLFM waveform...")
                        
        

                # set_params= params.copy()
                # start_freqs = np.arange(float(params["start_frequency"]), float(params["stop_frequency"]) + 0.0001, float(params["step_frequency"]))
                # print("Start frequency sweep :",start_freqs)
                # set_params = params.copy()
                # set_params.pop("start_frequency")
                # set_params.pop("stop_frequency")
                # set_params.pop("step_frequency")
                # set_params["start_frequency"] = None
                



    def sendWaveform(self, channel, waveform, set_params, amps, writer):
        self.gui.adqfig.clear()
        ax1 = self.gui.adqfig.add_subplot(2, 1, 1)
        ax2 = self.gui.adqfig.add_subplot(2, 1, 2)
        t = self.generator._build_time_axis(duration_s=self.gui.params["signal_duration"], sampling_frequency = 1e9)
        for chtype, chno in channel.items():
            if chtype == 'data':
                pass
            elif chtype == 'rf_reference':
                if ref == 0:
                    pass
                elif ref == 1:
                    #time stretched
                    # fs = self.gui.params["stretch_factor"]
                    # set_params = 
                    pass
                elif ref == 2:
                    # time stretched and chopped
                    pass

            print(set_params)
            w = self.generator.generate_with_params(wftype=waveform, params=set_params, duration_s=self.gui.params["signal_duration"])
            # t, w = self.generator.sinusoidal(frequency=f, sampling_freq=self.gui.params["sampling_freq"])
            self.save_waveform_to_csv(w_values=w, channel=chtype, folder=self.folder_name)
            self.gui.log_box.append(f"Generated {waveform} waveform for channel {chtype} with parameters {set_params}")
            local = self.folder_name+chtype+".csv"
            awgFile = self.remote_path+chtype+".csv"
            self.awg.transfer_waveform(LOCAL_FILE=local , AWG_FILE=awgFile)
            self.awg.import_file(channel=chno,filename= awgFile)
        for amp in amps:
            for chtype, chno in channel.items():
                self.awg.set_output_voltage_custom(chno, amp)
                self.gui.log_box.append(f"Set amplitude {amp} V for channel {chtype}")
                self.awg.set_output_state(chno, 1)
            self.awg.initiate_signal()
            print("Waiting for signal to generate...")
            # time.sleep(self.gui.params['awg_delay'])
            time.sleep(1)
            print("Read data")
            # adq_data = self.adq.acquire_voltage_reading()
            adq_data = self.adq.acquire_reading()
            data = (adq_data[self.gui.params['adq_channel']['params']['data']]* 1.92 / 2**15).tolist()
            ref = (adq_data[self.gui.params['adq_channel']['params']['rf_reference']]* 1.92 / 2**15).tolist()
            print("Element type", type(data[1]))
            print("Datatype:",type(data))
            print("Length:", len(data))
            self.awg.abort_wave_generation()
            # writer.writerow([f, amp, adq_data[self.gui.params['adq_channel']['params']['data']].tolist(), adq_data[self.gui.params['adq_channel']['params']['reference']].tolist()])
            print(set_params)
            writer.writerow(list(set_params.values())+[amp, data, ref])
            self.plot_waveform_and_spectrum(t, np.array(data), self.gui.adqfig, self.gui.adqcanvas,  ax1, ax2, fs=self.gui.params["adq_sampling_freq"], spectype=self.gui.params["adq_visualization"])
            print("saved")
        

    def validate_inputs(self, channel, waveform_type,combine=False):
        """Validate inputs based on waveform type"""
        if combine:
            start_amp = float(getattr(self.gui, f'combined_start_amp').text().strip())
            stop_amp = float(getattr(self.gui, f'combined_stop_amp').text().strip())
            step_amp = float(getattr(self.gui, f'combined_step_amp').text().strip())
        
            if not (0.1 <= start_amp<= 0.7):
                return False, f"Start amp must be 100-700mV got ({start_amp})"
            if not (0.1 <= stop_amp <= 0.7):
                return False, f"Stop amp must be 100-700mV got ({stop_amp}"
            if stop_amp < start_amp:
                return False, f"Stop amp ({stop_amp}) must be > Start amp ({start_amp})"
            if stop_amp < step_amp:
                return False, f"Stop amp ({stop_amp}) must be > Step amp ({step_amp})"
            

            if waveform_type == "Sine":
                    start_freq = float(getattr(self.gui, f'combined_start_freq').text().strip())
                    stop_freq = float(getattr(self.gui, f'combined_stop_freq').text().strip())
                    step_freq = float(getattr(self.gui, f'combined_step_freq').text().strip())
                
                    if not (0.0 <= start_freq <= 4.0):
                        return False, f"Start freq must be 0-4GHz got { start_freq})"
                    if not (0.0 <= stop_freq <= 4.0):
                        return False, f"Stop freq must be 0-4GHz got {stop_freq})"
                    if stop_freq < start_freq:
                        return False, f"Stop freq ({stop_freq}) must be >= Start freq ({start_freq})"
                    if stop_freq < step_freq:
                        return False, f"Stop freq ({stop_freq}) must be >= Step freq ({step_freq})"
                    
                    if (not getattr(self.gui, f'combined_start_freq').text().strip() or
                         not getattr(self.gui, f'combined_stop_freq').text().strip() or
                         not getattr(self.gui, f'combined_step_freq').text().strip() or
                         not getattr(self.gui, f'combined_start_amp').text().strip() or 
                         not getattr(self.gui, f'combined_stop_amp').text().strip() or
                    not getattr(self.gui, f'combined_step_amp').text().strip()):
                        return False, "All inputs are required!!!"
                
            
            elif waveform_type == "PRBS":
                if (not getattr(self.gui, f'combined_start_order').text().strip() or
                    not getattr(self.gui, f'combined_stop_order').text().strip() or
                    not getattr(self.gui, f'combined_step_order').text().strip() or
                    not getattr(self.gui, f'combined_start_amp').text().strip() or 
                    not getattr(self.gui, f'combined_stop_amp').text().strip() or
                    not getattr(self.gui, f'combined_step_amp').text().strip() or
                    not getattr(self.gui, f'combined_prbs_repetition_rate').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif waveform_type == "LFM":
                BW = float(getattr(self.gui, f'combined_lfm_bandwidth').text().strip())
                scf = float(getattr(self.gui, f'combined_start_center_freq').text().strip())
                spcf = float(getattr(self.gui, f'combined_stop_center_freq').text().strip())
                step_cf = float(getattr(self.gui, f'combined_step_center_freq').text().strip())
                sampling_period = 1/self.sampling_frequency
                pulse_width = float(getattr(self.gui, f'combined_lfm_pulse_width').text().strip())
                if not (0.0 <= scf <= 4.0):
                    return False, f"Start freq must be 0-4GHz got { scf})"
                if not (0.0 <= BW <= 4.0):
                    return False, f"Bandwidth must be 0-4GHz got {BW})"
                # if not (0.0 <= pulse_width <= 4.0):
                #     return False, f"pulse width must be 0-4GHz got {pulse_width})"
                if not (0.0 <= spcf <= 4.0):
                    return False, f"Stop freq must be 0-4GHz got {spcf})"
                if spcf < scf:
                    return False, f"Stop freq ({spcf}) must be >= Start freq ({scf})"
                if spcf < step_cf:
                    return False, f"Stop freq ({spcf}) must be >= Step freq ({step_cf})"
                if not (scf+BW==spcf):
                    return False, f"Stop center freq ({spcf}) must be > Start center freq ({scf})+ bandwidth ({BW})"
                if not (pulse_width>sampling_period):
                    return False, f"pulse width ({pulse_width}) must be > sampling period ({sampling_period})"
                if spcf < step_cf:
                        return False, f"Stop freq ({spcf}) must be >= Step freq ({step_cf})"
                
                if (not getattr(self.gui, f'combined_start_center_freq').text().strip() or
                    not getattr(self.gui, f'combined_stop_center_freq').text().strip() or  
                    not getattr(self.gui, f'combined_step_center_freq').text().strip() or 
                    not getattr(self.gui, f'combined_lfm_pulse_width').text().strip() or 
                    not getattr(self.gui, f'combined_lfm_bandwidth').text().strip() or
                    not getattr(self.gui, f'combined_start_amp').text().strip() or
                    not getattr(self.gui, f'combined_stop_amp').text().strip() or
                    not getattr(self.gui, f'combined_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif waveform_type == "Noise":
                if (not getattr(self.gui, f'combined_start_variance').text().strip() or
                    not getattr(self.gui, f'combined_stop_variance').text().strip() or
                    not getattr(self.gui, f'combined_step_variance').text().strip() or
                    not getattr(self.gui, f'combined_duration').text().strip() or
                    not getattr(self.gui, f'combined_start_amp').text().strip() or 
                    not getattr(self.gui, f'combined_stop_amp').text().strip() or
                    not getattr(self.gui, f'combined_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif waveform_type == "stepLFM":

                s_start_freq = float(getattr(self.gui, f'combined_lfm_start_freq').text())
                s_stop_freq = float(getattr(self.gui, f'combined_lfm_stop_freq').text())
                s_step_freq = float(getattr(self.gui, f'combined_lfm_step_freq').text())
                sampling_period = 1/self.sampling_frequency
                dwell_time = float(getattr(self.gui, f'combined_lfm_dwell_time').text())

                if not (0.0 <= s_start_freq <= 4.0):
                    return False, f"Start freq must be 0-4GHz got {s_start_freq})"
                if not (0.0 <= s_stop_freq <= 4.0):
                    return False, f"Stop freq must be 0-4GHz got {s_stop_freq})"
                if s_stop_freq <= s_start_freq:
                    return False, f"Stop freq ({s_stop_freq}) must be > Start freq ({s_start_freq})"
                if s_stop_freq <= s_step_freq:
                    return False, f"Stop freq ({s_stop_freq}) must be > Step freq ({s_step_freq})"
                if not (dwell_time>sampling_period):
                    return False, f"dwell time ({dwell_time}) must be > sampling period ({sampling_period})"
                
                if (not getattr(self.gui, f'combined_lfm_start_freq').text().strip() or
                    not getattr(self.gui, f'combined_lfm_stop_freq').text().strip() or  
                    not getattr(self.gui, f'combined_lfm_step_freq').text().strip() or 
                    not getattr(self.gui, f'combined_lfm_dwell_time').text().strip() or
                    not getattr(self.gui, f'combined_start_amp').text().strip() or
                    not getattr(self.gui, f'combined_stop_amp').text().strip() or
                    not getattr(self.gui, f'combined_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
        elif channel == 1 or channel == 2:
            start_amp = float(getattr(self.gui, f'ch{channel}_start_amp').text().strip())
            stop_amp = float(getattr(self.gui, f'ch{channel}_stop_amp').text().strip())
            step_amp = float(getattr(self.gui, f'ch{channel}_step_amp').text().strip())

            if not (0.1 <= start_amp <= 0.7):
                return False, f"Start amp must be 100-700mV got ({start_amp})"
            if not (0.1 <= stop_amp <= 0.7):
                return False, f"Stop amp must be 100-700mV got ({stop_amp}"
            if stop_amp < start_amp:
                return False, f"Stop amp ({stop_amp}) must be > Start amp ({start_amp})"
            if stop_amp < step_amp:
                return False, f"Stop amp ({stop_amp}) must be > Step amp ({step_amp})"
                    

            if waveform_type == "Sine":
                    start_freq = float(getattr(self.gui, f'ch{channel}_start_freq').text().strip())
                    stop_freq = float(getattr(self.gui, f'ch{channel}_stop_freq').text().strip())
                    step_freq = float(getattr(self.gui, f'ch{channel}_step_freq').text().strip())
                
                    if not (0.0 <= start_freq <= 4.0):
                        return False, f"Start freq must be 0-4GHz got { start_freq})"
                    if not (0.0 <= stop_freq <= 4.0):
                        return False, f"Stop freq must be 0-4GHz got {stop_freq})"
                    if stop_freq < start_freq:
                        return False, f"Stop freq ({stop_freq}) must be >= Start freq ({start_freq})"
                    if stop_freq < step_freq:
                        return False, f"Stop freq ({stop_freq}) must be >= Step freq ({step_freq})"
                    
                    if (not getattr(self.gui, f'ch{channel}_start_freq').text().strip() or
                         not getattr(self.gui, f'ch{channel}_stop_freq').text().strip() or
                         not getattr(self.gui, f'ch{channel}_step_freq').text().strip() or
                         not getattr(self.gui, f'ch{channel}_start_amp').text().strip() or 
                         not getattr(self.gui, f'ch{channel}_stop_amp').text().strip() or
                         not getattr(self.gui, f'ch{channel}_step_amp').text().strip()):
                        return False, "All inputs are required!!!"
                     
            
            elif waveform_type == "PRBS":
                if (not getattr(self.gui, f'ch{channel}_start_order').text().strip() or
                    not getattr(self.gui, f'ch{channel}_stop_order').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_order').text().strip() or
                    not getattr(self.gui, f'ch{channel}_start_amp').text().strip() or 
                    not getattr(self.gui, f'ch{channel}_stop_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_prbs_repetition_rate').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif waveform_type == "LFM":
                BW = float(getattr(self.gui, f'ch{channel}_lfm_bandwidth').text().strip())
                scf = float(getattr(self.gui, f'ch{channel}_start_center_freq').text().strip())
                spcf = float(getattr(self.gui, f'ch{channel}_stop_center_freq').text().strip())
                step_cf = float(getattr(self.gui, f'ch{channel}_step_center_freq').text().strip())
                sampling_period = 1/self.sampling_frequency
                pulse_width = float(getattr(self.gui, f'ch{channel}_lfm_pulse_width').text().strip())

                if not (0.0 <= scf <= 4.0):
                    return False, f"Start freq must be 0-4GHz got { scf})"
                if not (0.0 <= BW <= 4.0):
                    return False, f"Bandwidth must be 0-4GHz got {BW})"
                # if not (0.0 <= pulse_width <= 4.0):
                #     return False, f"pulse width must be 0-4GHz got {pulse_width})"
                if not (0.0 <= spcf <= 4.0):
                    return False, f"Stop freq must be 0-4GHz got {spcf})"
                if spcf < scf:
                    return False, f"Stop freq ({spcf}) must be >= Start freq ({scf})"
                if spcf < step_cf:
                    return False, f"Stop freq ({spcf}) must be >= Step freq ({step_cf})"
                if not (scf+BW==spcf):
                    return False, f"Stop center freq ({spcf}) must be > Start center freq ({scf})+ bandwidth ({BW})"
                if not (pulse_width>sampling_period):
                    return False, f"pulse width ({pulse_width}) must be > sampling period ({sampling_period})"
                if spcf < step_cf:
                        return False, f"Stop freq ({spcf}) must be >= Step freq ({step_cf})"
                
                if (not getattr(self.gui, f'ch{channel}_start_center_freq').text().strip() or
                    not getattr(self.gui, f'ch{channel}_stop_center_freq').text().strip() or  
                    not getattr(self.gui, f'ch{channel}_step_center_freq').text().strip() or 
                    not getattr(self.gui, f'ch{channel}_lfm_pulse_width').text().strip() or 
                    not getattr(self.gui, f'ch{channel}_lfm_bandwidth').text().strip() or
                    not getattr(self.gui, f'ch{channel}_start_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_stop_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif waveform_type == "Noise":
                if (not getattr(self.gui, f'ch{channel}_start_variance').text().strip() or
                    not getattr(self.gui, f'ch{channel}_stop_variance').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_variance').text().strip() or
                    not getattr(self.gui, f'ch{channel}_duration').text().strip() or
                    not getattr(self.gui, f'ch{channel}_start_amp').text().strip() or 
                    not getattr(self.gui, f'ch{channel}_stop_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif waveform_type == "stepLFM":

                s_start_freq = float(getattr(self.gui, f'ch{channel}_lfm_start_freq').text())
                s_stop_freq = float(getattr(self.gui, f'ch{channel}_lfm_stop_freq').text())
                s_step_freq = float(getattr(self.gui, f'ch{channel}_lfm_step_freq').text())
                sampling_period = 1/self.sampling_frequency
                dwell_time = float(getattr(self.gui, f'ch{channel}_lfm_dwell_time').text())

                if not (0.0 <= s_start_freq <= 4.0):
                    return False, f"Start freq must be 0-4GHz got {s_start_freq})"
                if not (0.0 <= s_stop_freq <= 4.0):
                    return False, f"Stop freq must be 0-4GHz got {s_stop_freq})"
                if s_stop_freq <= s_start_freq:
                    return False, f"Stop freq ({s_stop_freq}) must be > Start freq ({s_start_freq})"
                if s_stop_freq <= s_step_freq:
                    return False, f"Stop freq ({s_stop_freq}) must be > Step freq ({s_step_freq})"
                if not (dwell_time>sampling_period):
                    return False, f"dwell time ({dwell_time}) must be > sampling period ({sampling_period})"
                
                if (not getattr(self.gui, f'ch{channel}_lfm_start_freq').text().strip() or
                    not getattr(self.gui, f'ch{channel}_lfm_stop_freq').text().strip() or  
                    not getattr(self.gui, f'ch{channel}_lfm_step_freq').text().strip() or 
                    not getattr(self.gui, f'ch{channel}_lfm_dwell_time').text().strip() or
                    not getattr(self.gui, f'ch{channel}_start_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_stop_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
                
            elif self.gui.ch1_upload_check_bx.isChecked() or self.gui.ch2_upload_check_bx.isChecked():
                if (not getattr(self.gui, f'ch{channel}_start_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_stop_amp').text().strip() or
                    not getattr(self.gui, f'ch{channel}_step_amp').text().strip()):
                    return False, "All inputs are required!!!"
        
                  
        return True, ""
    
    
    def sinc_interpolation(self,data_ch,interpolationRate=2):
        x2 = np.r_[0:len(data_ch):len(data_ch) * 1j]
        v = len(data_ch) * interpolationRate
        x2_new = np.r_[0:len(data_ch):(v) * 1j]
        x = data_ch
        s = x2
        u = x2_new
        if len(x) != len(s):
            raise ValueError('x and s must be the same length')

        # Find the period
        T = s[1] - s[0]

        sincM = np.tile(u, (len(s), 1)) - np.tile(s[:, np.newaxis], (1, len(u)))
        y = np.dot(x, np.sinc(sincM / T))
        return y
    
    
    def calculatespectrogram(self,data,fs):
        '''
        Calculate spectrogram of the input signal using scipy.signal.spectrogram and convert to dBm scale for plotting.
        
        Parameters:
        data        : V, np.array(), array of the input signal
        fs          : Hz, float, sampling frequency in Hz
        Returns:
        f_spec      : Hz, np.array(), array of frequency bins in Hz
        t_spec      : s, np.array(), array of time bins in seconds
        Sxx_bin_dBm : dBm, np.array(), 2D array of spectrogram power values
        '''
        f_spec, t_spec, Sxx = signal.spectrogram(data,fs=fs,nperseg=512,noverlap=256,window='hann')
        df = f_spec[1] - f_spec[0] #Freq bin width ,Ar
        Sxx_bin_W = (Sxx / 50) * df # convert Psd into power per bin in watts asssuming 50 ohm system
        Sxx_bin_dBm =10*np.log10(Sxx_bin_W * 1e3) # convert to dBm
        return f_spec, t_spec, Sxx_bin_dBm
        

    def handleadqupdate(self):
        samples = int(self.gui.adqsamples.text())
        interp = int(self.gui.adqinterpolation.text())
        channel = self.gui.adqchannel.currentText()
        
        # Initialize ADQ reader (reuse ADQ14.py logic)
        reader = ADQ14Reader(samples_per_record=samples)
        data = reader.acquire_reading()  # Shape: records, samples, channels
        print(channel)
        ch_idx = {"A":0, "B":1, "C":2, "D":3}[channel]
        print(ch_idx)
        ch_data = data[ch_idx] * 1.92 / 2**15  # Voltage conversion [file:2]
        interpolated_data = self.sinc_interpolation(ch_data,interp)
        self.gui.adqfig.clear()
        ax = self.gui.adqfig.add_subplot(211)
        ax2 = self.gui.adqfig.add_subplot(212)

        # Time domain plot
        time_ns = np.arange(len(interpolated_data)) *1.0
        ax.plot(time_ns, interpolated_data)
        ax.set_xlabel('Sampled time (ns)')
        ax.set_ylabel('Amplitude (V)')
        ax.grid(True)
        ax.set_title(f'ADQ Channel {channel}')
        fs=1e9/interp
        
        # FFT if checked
        if self.gui.adqfftcheck.isChecked():
            f_MHz,power_dBm = self.fft_signal(interpolated_data, fs)
            ax2.plot(f_MHz,power_dBm)
            # ax2.semilogy(f_MHz,power_dBm,'r--')
            ax2.set_xlabel("F (GHz)")
            ax2.set_ylabel("Power(dBm)")
            ax2.grid(True)
        
        # Spectrogram if checked (replaces main plot)
        elif self.gui.adqspectrocheck.isChecked():
            f_spec, t_spec, Sxx_bin_dBm = self.calculatespectrogram(interpolated_data,fs)
            # self.gui.adqfig.clear()  # Replace with spectrogram
            # ax = self.gui.adqfig.add_subplot(111)
            im = ax2.pcolormesh(t_spec*1e9, f_spec/1e6, Sxx_bin_dBm, shading='gouraud')
            vmax = np.max(Sxx_bin_dBm)    #ar
            vmin = vmax - 10  # show 10 dB dynamic range
            im.set_clim(vmin, vmax)
            cbar = self.gui.adqfig.colorbar(im, ax=ax2) #ar
            
            cbar.set_label('Power [dBm]')
            ax2.set_ylabel('Freq [MHz]')
            ax2.set_xlabel('Time [ns]')
        
        self.gui.adqfig.tight_layout()
        self.gui.adqcanvas.draw()
        reader.close()


    def save_waveform_to_csv(self, w_values, channel, folder):
        """Save waveform data to a CSV file."""
        self.folder = folder
        if not self.folder:
            self.gui.log_box.append("⚠️ Save operation cancelled by user.")
            return None

        filename = f"{channel.lower()}.csv"

        try:
            full_path = os.path.join(self.folder, filename)
            print(full_path)

            with open(full_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                for a in w_values:
                    writer.writerow([a])
            self.gui.log_box.append(f"✅ Channel {channel} waveform data saved to: {full_path}")
            return full_path
        except Exception as e:
            self.gui.log_box.append(f"❌ Error saving waveform: {e}")
            return None


    '''def check_awg_connection(self):
        """Check if AWG is connected"""
        if not self.awg:
            self.gui.log_box.append("❌ AWG not connected. Please connect first.")
            return False
        return True'''
    

    def handle_connect(self):
        """Handle AWG connection"""
        ip = self.gui.params["awg_ip"].strip()
        # Enable tabs if AWG is connected
        if not ip:
            self.gui.log_box.append("❌ Please enter AWG IP address")
            QMessageBox.warning(self.gui, "Input Required", "Please enter AWG IP address")
            self.gui.ip_input.setFocus()
            self.gui.status_light.set_connected(False)
            return
        try:
            self.awg = TektronixAWG(ip_address=ip)
            # self.awg = AWG_Controller(ip_address=ip)
            connect = self.awg.connect()
            if connect:
                self.gui.status_light.set_connected(True)
                # self.gui.combined_waveform_tab.setEnabled(True)
                self.gui.log_box.append(f"🔌 Connected to AWG at {ip}")
            else:
                QMessageBox.warning(self.gui, "Connection failed", f"Connection failed \n Ensure AWG and PC are on same network!")

        except Exception as e:
            QMessageBox.warning(self.gui, 'Error!!', f"Connection error \n {e}")
            self.gui.log_box.append(f"failed to connect to AWG \n {e}")

        
    def handle_disconnect(self):
        """Handle AWG disconnection"""
        if self.awg:
            try:
                self.awg.disconnect()
                self.gui.status_light.set_connected(False)
                self.gui.log_box.append("🔌 Disconnected from AWG")

            except Exception as e:
                self.gui.log_box.append(f"❌ Disconnect error: {e}")


    def handle_abort(self):
        """Abort waveform generation for specified channel"""
        if not self.awg.is_connected():
            return
        try:
            self.awg.abort_wave_generation()
        except Exception as e:
            self.gui.log_box.append(f"❌ Failed to abort waveform generation: {e}")


    def closeEvent(self, event):
        """Handle application close event"""
        if self.awg is not None:
            if hasattr(self, 'worker_ch1') and self.worker_ch1 is not None and self.worker_ch1.isRunning():
                self.worker_ch1.stop()
                self.worker_ch1.quit()
                self.worker_ch1.wait()
            if hasattr(self, 'worker_ch2') and self.worker_ch2 is not None and self.worker_ch2.isRunning():
                self.worker_ch2.stop()
                self.worker_ch2.quit()
                self.worker_ch2.wait()
            self.awg.disconnect()
            self.adq.close()
        event.accept()


    def fft_signal(self, w, sampling_freq, iota=2):
        """
        Compute FFT of signal and return shifted frequency axis.
        Args:
            w (ndarray): input waveform
            sampling_freq (float): sampling frequency in Hz (default 8 GHz)
        """
        N = len(w)
        # FFT
        x = fftshift(fft(w))
        P_W = (np.abs(x) / N) ** 2 /(50 *2)  # normalize magnitude
        P_dBm = 10 * np.log10(P_W / 1e-3)  # reference 1 mW    
        # Frequency axis
        freq = fftshift(fftfreq(N, d=1/sampling_freq)) / 1e9
        return freq, P_dBm
    

    
    
    def handle_browse_file(self, channel):
        file_path = QFileDialog.getExistingDirectory(self.gui, "Select Folder to Save CSV")

        if file_path:
            if channel == 1:
                self.gui.ch1_file_path_input.setText(file_path)
            elif channel == 2:
                self.gui.ch2_file_path_input.setText(file_path)
 

    def handle_combined_waveform(self, channel):
        try:
            num_samples = int(self.gui.num_samples.text().strip())
            waveform_specs = []
            # Use your existing combined-tab widgets:
            # self.waveboxes[i] (checkboxes)
            # self.dropdownboxes[i] (QComboBox with "Sine", "PRBS", "LFM", "Step LFM", "Noise")
            for i, cb in enumerate(self.gui.wave_boxes):
                if not cb.isChecked():
                    continue
                if i not in self.gui.combined_params_per_wave:
                    continue
                pd=self.gui.combined_params_per_wave[i]
                wftype=pd["type"]
                if wftype == "Select":
                    continue
                if wftype == "Sine":
                    freq = pd["combined_freq"].text().strip()
                    params = {
                        "frequency": freq
                    }

                elif wftype == "LFM":
                    cf = pd["combined_center_freq"].text().strip()
                    bw = pd["combined_bandwidth"].text().strip()
                    pw = pd["combined_pulse_width"].text().strip()
                    params = {
                        "centerfreq": cf,
                        "bandwidth": bw,
                        "pulsewidth": pw
                        
                    }

                elif wftype == "Step_LFM":
                    sf = pd["combined_start_freq"].text().strip()
                    ef = pd["combined_stop_freq"].text().strip()
                    st = pd["combined_step_freq"].text().strip()
                    dt = pd["combined_dwell_time"].text().strip()
                    params = {
                        "startfreq": sf,
                        "stopfreq": ef,
                        "stepfreq": st,
                        "dwelltime": dt
                        
                    }

                elif wftype == "Noise":
                    var_ = pd["combined_variance"].text().strip()
                    params = {
                        "variance": var_
                    }

                else:
                    # Ignore PRBS for now unless you add its logic
                    continue
                print(params)
                waveform_specs.append({"type": wftype, "params": params})

            if not waveform_specs:
                QMessageBox.warning(self.gui, "Input Required", "Select at least one waveform in Combined tab.")
                return
            print(waveform_specs)
            # Generate superimposed waveform
            t, w_sum = self.combined_gen.generate_superimposed(waveform_specs, num_samples)

            # Plot exactly like CH1/CH2 but using combfig/combcanvas
            fig = self.gui.combfig
            canvas = self.gui.combcanvas
            fig.clear()
            ax1 = fig.add_subplot(2, 1, 1)
            ax2 = fig.add_subplot(2, 1, 2)
            self.plot_waveform_and_fft("combined", t, w_sum, fig, canvas, ax1, ax2, self.sampling_frequency)

            # Save using existing helper
            ch_folder = QFileDialog.getExistingDirectory(self.gui, "Select Folder to Save CSV")
            if not ch_folder:
                return
            datetime_1 = datetime.now().strftime("%Y%m%d%H%M")
            self.folder_name = f"combined_{datetime_1}"
            full_path = os.path.join(ch_folder, self.folder_name)
            os.makedirs(full_path, exist_ok=True)

            self.save_waveform_to_csv(
                w_values=w_sum,
                waveform_type="CombinedSuperimposed",
                channel=channel,
                folder=full_path
            )

            self.gui.log_box.append(f"Superimposed waveform generated and saved, {len(w_sum)} samples.")

            self.handle_upload_waveform(file_path=full_path, channel=channel,combine=True)  
        except Exception as e:
            self.gui.log_box.append(f"Error in combined superposition: {e}")
         
    
    def handle_adq14_disconnect(self):
        """Handle ADQ14 disconnection"""
        try:
            self.gui.log_box.append("🔌 Disconnected from ADQ14")
            self.gui.adqfig.clear()
            self.gui.adqcanvas.draw()
        except Exception as e:
            self.gui.log_box.append(f"❌ Failed to disconnect from ADQ14: {e}")

    
    
    def handle_adq14_connect(self):
        """Handle ADQ14 connection"""
        try:
            num_samples = int(self.gui.params["signal_duration"]* 1e9)
            self.adq = ADQ14Reader(device_num=1, samples_per_record=num_samples, number_of_records=1, trigtype=1)
            print(self.gui.params)
            self.gui.log_box.append("🔌 Connected to ADQ14")
        except Exception as e:
            self.gui.log_box.append(f"❌ Failed to connect to ADQ14: {e}")

    

    def run_callback(self, amplitude):
        self.logger.info("AWGCommunicator thread started.")
        try:
            if self.awg is None:
                self.logger.error("AWG is not connected.")
                return
            
            self.awg.set_amplitude(self.channel, amplitude)
            self.logger.info(f"Set amplitude {amplitude} on channel {self.channel}.")
            self.aw
            self.logger.info("AWGCommunicator thread stopped.")
        except Exception as e:
            self.logger.error(f"Error in AWGCommunicator thread: {e}")

