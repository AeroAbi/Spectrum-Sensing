import numpy as np
import pandas as pd 
from scipy import signal
from pyfinite import ffield
from logger import awg_logger
import fractions
from fractions import Fraction
from numpy.fft import fft, fftshift, fftfreq

# Create a class to generate waveforms

class WaveformGenerator:
    
    sampling_frequency =25e9
    def __init__(self, sampling_frequency=sampling_frequency):
        self.sampling_frequency = float(sampling_frequency)
        self.logger = awg_logger('WaveformGenerator')
        
    # Sinusoidal wave
    def sinusoidal(self, frequency_ghz, duration_s=None, **kwargs):
        '''
        Generate a sinusoidal waveform:
        
        Parameters:
        frequency_ghz : float, GHz, frequency of the sine wave
        duration_s     : float, seconds, duration of the sine wave (if None, use integer number of periods)
        
        Returns:
        t : numpy array, time axis [s]
        waveform : numpy array, waveform amplitude
        '''
        frequency_hz = float(frequency_ghz) * 1e9  # user gives frequency in GHz
        if duration_s is not None:
            time=self._build_time_axis(float(duration_s))  # time in seconds based on duration and sampling frequency
        else:
            k=frequency_hz/self.sampling_frequency
            n=Fraction(k).limit_denominator(10000000).denominator
            time = self._build_time_axis(n / self.sampling_frequency)  # build time axis for integer number of periods to avoid discontinuities
            print(n,k)
        
        wave = np.sin(2 * np.pi * frequency_hz * time)
        
        response = f"Generated num samples: {len(wave)}, frequency: {frequency_ghz} GHz, sampling freq: {self.sampling_frequency/1e9} GHz"
        self.logger._log_command(command="generate sine wave", duration_ms=None, response = response)
        print(response)
        print(frequency_hz)

        return  time, wave


    def generate_lfm(self, center_freq_ghz, bandwidth_ghz, pulse_width_ns, duration_s = None ,**kwargs):
        '''
        Generate a Linear Frequency Modulated (LFM) waveform:
        
        Parameters:
        center_freq     : float, GHz, center frequency of the LFM signal
        bandwidth       : float, GHz, bandwidth of the LFM signal
        pulse_width     : float, seconds, duration of the LFM pulse
        duration_s      : float, seconds, total duration of the LFM waveform (if None, use pulse_width)

        Returns:
        t               : numpy array, time axis [s] 
        waveform        : numpy array, waveform amplitude
        '''
        # center_freq_hz = float(center_freq_ghz) * 1e9  # GHz to Hz
        # pulse_width_s = float(pulse_width_ns) * 1e-9  # pulse_width is in ns, convert to seconds
        # bandwidth_hz = float(bandwidth_ghz * 1e9)
        # if duration_s is not None:
        #     t=self._build_time_axis(float(duration_s))
        # else:
        #     c=pulse_width_s*self.sampling_frequency
        #     n=Fraction(c).limit_denominator(10000000).denominator
        #     t = self._build_time_axis(n / self.sampling_frequency)  # build time axis for integer number of periods to avoid discontinuities
        # k = bandwidth_hz/pulse_width_s
        # f0 = float(center_freq_hz - bandwidth_hz / 2)
        # f1 = float(center_freq_hz + bandwidth_hz / 2)
        # waveform = np.cos(2*np.pi * ((f0 * t) + (k/2) * (t ** 2)))   #signal.chirp(t, f0=self.f0, f1=self.f1, t1=self.pulse_width, method='linear') 

        center_freq_hz = float(center_freq_ghz) * 1e9
        pulse_width_s = float(pulse_width_ns) * 1e-9
        bandwidth_hz = float(bandwidth_ghz) * 1e9
        if duration_s is not None:
            n = int(round(duration_s * self.sampling_frequency))
            T = n / self.sampling_frequency
            t = self._build_time_axis(T)
        else:
            # Step 1: integer samples
            n = int(round(pulse_width_s * self.sampling_frequency))
            T = n / self.sampling_frequency
            t = self._build_time_axis(T)

        # Step 2: chirp params
        k = bandwidth_hz / pulse_width_s
        f0 = center_freq_hz - bandwidth_hz / 2

        # Step 3: phase correction
        phase_cycles = f0*T + 0.5*k*T**2
        N = round(phase_cycles)
        k_corrected = (2 * (N - f0*T)) / (T**2)

        # Step 4: waveform
        waveform = np.cos(2*np.pi * (f0*t + 0.5*k_corrected*t**2))

        return t, waveform
    
    
    # def generate_steplfm(self,start_freq_ghz, stop_freq_ghz, step_freq_ghz, dwell_time_ns, duration_s, **kwargs):
    def generate_steplfm(self,fstart_initial_ghz, fstart_final_ghz, step_freq_ghz,stepLFM_ghz,StepLFM_Nstep, dwell_time_ns, duration_s, **kwargs):    
        """
        Generate a Step-LFM waveform:
        Parameters:
        start_freq    : float, GHz, starting frequency
        stop_freq     : float, GHz, stopping frequency (inclusive)
        step_freq     : float, GHz, frequency increment per step
        dwell_time    : float, nanoseconds, duration of each step
        sampling_freq : float, GHz, sampling frequency (default: 8 GHz)
        Returns:
        t_total : numpy array, time axis [ns] 
        waveform : numpy array, waveform amplitude
        """
        """
        If 'duration' is given (seconds), build a step-LFM on that grid using the same
        start/stop/step and dwell_time logic. Otherwise, use existing concatenation logic.
        """
        # ##updated##
        fstart_initial_freq_hz = float(fstart_initial_ghz) * 1e9   # GHz to Hz
        fstart_final_freq_hz  = float(fstart_final_ghz) * 1e9   # GHz to Hz
        fstart_step_freq_hz  = float(step_freq_ghz) * 1e9   # GHz to Hz

        StepLFM_stepfreq_hz  = float(stepLFM_ghz) * 1e9   # GHz to Hz
        dwell_time_s  = float(dwell_time_ns) * 1e-9  # dwell_time is in ns, convert to seconds
        sampling_freq_hz = float(self.sampling_frequency)  # GHz to Hz
        StepLFM_Nstep = int(StepLFM_Nstep)
        dt = 1 / sampling_freq_hz

        start_freqs = np.arange(fstart_initial_freq_hz,fstart_final_freq_hz + 0.0001,fstart_step_freq_hz)  #check
        print("Start Frequency Sweep Values (GHz):", start_freqs)
        if duration_s is not None:
            time_axis = self._build_time_axis(float(duration_s))
            # Build on provided time grid
            t_total = np.asarray(time_axis)
            waveform = np.zeros_like(t_total, dtype=np.float64)

        # all_waveforms = []

        for step, fstart_current in enumerate(start_freqs):

            waveform = np.zeros_like(t_total)
            # fstop_current = fstart_current + (StepLFM_Nstep - 1)*StepLFM_stepfreq_hz
            # print(f"Sweep {step+1}: Start {fstart_current/1e9:.2f} GHz, Stop {fstop_current/1e9:.2f} GHz")

            for n in range(StepLFM_Nstep):

                current_freq = fstart_current + n *StepLFM_stepfreq_hz
                t_start = n*dwell_time_s
                t_end = t_start + dwell_time_s
                mask = (t_total >= t_start) & (t_total < t_end)
                t_seg = t_total[mask] - t_start
                waveform[mask] = 0.25 * np.cos(2*np.pi*current_freq*t_seg)

            # all_waveforms.append(waveform.copy())
        # sum_signal = np.sum(all_waveforms, axis=0)
            # print(waveform)
        return t_total, waveform
  ##generated##
    # def generate_steplfm(self, fstart_ghz, stepLFM_ghz, StepLFM_Nstep, dwell_time_ns, duration_s, **kwargs):

    #     fstart_hz = float(fstart_ghz) * 1e9
    #     stepLFM_hz = float(stepLFM_ghz) * 1e9
    #     dwell_time_s = float(dwell_time_ns) * 1e-9
    #     StepLFM_Nstep = int(StepLFM_Nstep)

    #     t_total = np.asarray(self._build_time_axis(float(duration_s)))
    #     waveform = np.zeros_like(t_total, dtype=np.float64)

    #     for n in range(StepLFM_Nstep):
    #         current_freq = fstart_hz + n * stepLFM_hz
    #         t_start = n * dwell_time_s
    #         t_end = t_start + dwell_time_s

    #         mask = (t_total >= t_start) & (t_total < t_end)
    #         t_seg = t_total[mask] - t_start

    #         waveform[mask] = np.cos(2 * np.pi * current_freq * t_seg)

    #     return t_total, waveform

    # return t_total, waveform
    
    ###new##
    # def generate_steplfm(self,fstart_ghz,stepLFM_ghz,StepLFM_Nstep,dwell_time_ns,duration_s):

    #         # Convert units
    #     fstart_hz = fstart_ghz * 1e9
    #     step_hz = stepLFM_ghz * 1e9
    #     dwell_time_s = dwell_time_ns * 1e-9
    #     Fs = self.sampling_frequency
    #     dt = 1 / Fs

    #     # Time axis
    #     t_total = self._build_time_axis(duration_s)
    #     waveform = np.zeros_like(t_total)

    #      # Generate Step LFM
    #     for n in range(StepLFM_Nstep):

    #         current_freq = fstart_hz + n * step_hz

    #         t_start = n * dwell_time_s
    #         t_end = t_start + dwell_time_s

    #         mask = (t_total >= t_start) & (t_total < t_end)
    #         t_seg = t_total[mask] - t_start

    #     waveform[mask] = 2.5e-3 * np.cos(2 * np.pi * current_freq * t_seg)

    
    
    ##old##
        # start_freq_hz = float(start_freq_ghz) * 1e9   # GHz to Hz
        # stop_freq_hz  = float(stop_freq_ghz) * 1e9   # GHz to Hz
        # step_freq_hz  = float(step_freq_ghz) * 1e9   # GHz to Hz
        # dwell_time_s  = float(dwell_time_ns) * 1e-9  # dwell_time is in ns, convert to seconds
        # sampling_freq_hz = float(self.sampling_frequency)  # GHz to Hz
        
        # if duration_s is not None:
        #     time_axis = self._build_time_axis(float(duration_s))
        #     # Build on provided time grid
        #     t_total = np.asarray(time_axis)
        #     n_steps = int(np.floor((stop_freq_hz - start_freq_hz) / step_freq_hz)) + 1
        #     waveform = np.zeros_like(t_total, dtype=np.float64)
        #     for n in range(n_steps):
        #         current_freq = start_freq_hz + n * step_freq_hz
        #         t_start = n * dwell_time_s
        #         t_end = t_start + dwell_time_s
        #         mask = (t_total >= t_start) & (t_total < t_end)
        #         t_seg = t_total[mask] - t_start
        #         waveform[mask] = np.cos(2 * np.pi * current_freq * t_seg)
        # else:
        #     t_total = np.array([], dtype=np.float64)
        #     waveform = np.array([], dtype=np.float64)

        #     n_steps = int(np.floor((stop_freq_hz - start_freq_hz) / step_freq_hz)) + 1
        #     dt = 1 / sampling_freq_hz

        #     for n in range(n_steps):
        #         current_freq = start_freq_hz + n * step_freq_hz
        #         t_s = self._build_time_axis(dwell_time_s)  # time for one step
        #         wave = np.cos(2 * np.pi * current_freq * t_s)
        #         t_total = np.concatenate([t_total, t_s + n * dwell_time_s])
        #         waveform = np.concatenate([waveform, wave])
        # response = f"Generated Step LFM with start_freq: {start_freq_ghz} GHz, stop_freq: {stop_freq_ghz} GHz, step_freq: {step_freq_ghz} GHz, dwell_time: {dwell_time_ns} ns, total duration: {duration_s} s"
        # print(response)
        # self.logger._log_command(
        #     command="generate step LFM wave",
        #     duration_ms=None,
        #     response=response
        # )
        # return t_total, waveform
    
    
    def _build_time_axis(self, duration_s, **kwargs):
        """
        Common time axis in seconds.

        Parameters:
        duration : float, Total duration of the waveform in seconds.
        Returns:
        t : np.ndarray, Time axis in seconds, sampled at self.sampling_frequency, with length determined by duration.
        """
        if kwargs.get("sampling_frequency") is not None:
            sampling_frequency = kwargs.get("sampling_frequency")
        else:
            sampling_frequency = self.sampling_frequency
        t = np.arange(0, duration_s, 1 / sampling_frequency)

        return t
    

    def generate_with_params(self, wftype, params, duration_s):
        """
        Generate one waveform of given type and params, sampled on given time t.
        Uses WaveformGenerator, then resamples/interpolates onto t.
        """
        if wftype == "Sine":
            # params: {"frequency"}
            f = float(params["frequency"])
            # Generate with same numsamples & sampling freq
            _, w = self.sinusoidal(
                frequency_ghz=f,
                duration_s=duration_s
            )

        elif wftype == "LFM":
            # params: {"center_freq", "pulse_width", "bandwidth"}
            cf = float(params["center_frequency"])
            bw = float(params["bandwidth"])
            pw = float(params["pulse_width"])
            _, w = self.generate_lfm(
                center_freq_ghz=cf,
                bandwidth_ghz=bw,
                pulse_width_ns=pw,
                duration_s=duration_s
            )

        elif wftype == "StepLFM":  ##updated##

            sf = float(params["Start_frequency_initial"])
            ef = float(params["Start_frequency_final"])
            st = float(params["Start_frequency_step"])
            slfm = float(params["StepLFM_frequency"])
            nlfm = int(params["StepLFM_Nstep"])
            dt = float(params["dwell_time"])   
            _, w = self.generate_steplfm(
                fstart_initial_ghz=sf,
                fstart_final_ghz=ef,
                step_freq_ghz=st,
                dwell_time_ns=dt,
                stepLFM_ghz =slfm,
                StepLFM_Nstep = nlfm,
                duration_s=duration_s)
        
            # # params: {"start_freq", "stop_freq", "step_freq", "dwell_time"}
            # sf = float(params["start_frequency"])
            # ef = float(params["stop_frequency"])
            # st = float(params["step_frequency"])
            # dt = float(params["dwell_time"])
            # _, w = self.generate_steplfm(
            #     start_freq_ghz=sf,
            #     stop_freq_ghz=ef,
            #     step_freq_ghz=st,
            #     dwell_time_ns=dt,
            #     duration_s=duration_s
            

        else:
            raise ValueError(f"Unsupported combined waveform type: {wftype}")

        # If WaveformGenerator already uses the same sampling_frequency and numsamples,
        # t_loc should match t closely and we can just return w.
        # If not, one can interpolate here; for now, assume same grid:
        return w


    def generate_superimposed(self, waveform_specs, duration_s):
        """
        Generate superimposed waveform from multiple waveform specifications, all sampled on a common time axis.

        Parameters:
        waveform_specs : list of dict
            Each dict:
            {
              "type": "Sine" | "LFM" | "stepLFM",
              "params": {...}   # mapped from GUI inputs for that waveform
            }
        duration_ns : float
            Total duration of the superimposed waveform in nanoseconds.

        Returns:
        t : np.ndarray
            Common time axis in seconds.
        w_sum : np.ndarray
            Superimposed waveform (sum of all individual waves).
        """
        duration_s = float(duration_s)
        t = self._build_time_axis(duration_s=duration_s)  # common time axis for all waveforms, in seconds
        w_sum = np.zeros_like(t)

        for spec in waveform_specs:
                wftype = spec["type"]
                params = spec["params"]
                print(wftype, params)
                w = self.generate_with_params(wftype, params, duration_s=duration_s)
                w_sum += w
                max_amp = np.max(np.abs(w_sum))
                if max_amp > 0:
                    w_sum /= max_amp        # normalizing the amplitude #CHANGED 

        return t, w_sum
    
    
    def zero_pad(self, waveform, duration, sampling_frequency=None, position='after'):
        """
        Add zero padding to a waveform.
        Args:
            waveform (np.ndarray): Input waveform array.
            duration (float): Duration of zero padding in seconds.
            sampling_frequency (float, optional): Sampling frequency in Hz. If None, uses self.sampling_frequency.
            position (str): 'before' or 'after' to specify where to add the padding.
        Returns:
            np.ndarray: Waveform with zero padding added.
        """
        if sampling_frequency is None:
            sampling_frequency = self.sampling_frequency
        num_zeros = int(np.round(duration * sampling_frequency))
        zero_pad = np.zeros(num_zeros)
        if position == 'before':
            return np.concatenate([zero_pad, waveform])
        elif position == 'after':
            return np.concatenate([waveform, zero_pad])
        else:
            raise ValueError("position must be 'before' or 'after'")


    def get_taps(self, order):
        F = ffield.FField(order)
        taps = [i for i, bit in enumerate(reversed(F.ShowCoefficients(F.generator))) if bit == 1]
        print("taps: ", taps)
        return taps[:-1]  # remove x^0 term which is always 1 in primitive polynomials


    def PRBS(self, amplitude, order, repetition_rate, sampling_frequency=sampling_frequency, max_bits=None):
        amplitude = float(amplitude)
        order = int(order)
        taps = self.get_taps(order)
        sampling_frequency = float(sampling_frequency) 
        repetition_rate = float(repetition_rate) * 1e6

        oversample = round(sampling_frequency / repetition_rate)
        max_length = (2 ** order) - 1

        if max_bits is not None:
            length = min(max_length, int(max_bits))
        else:
            length = max_length

        while True:
            seed = np.random.randint(0, 2, size=order).tolist()
            if any(seed):
                break

        state = seed.copy()
        bits = []
        for _ in range(length):
            feedback = 0
            for t in taps:
                feedback ^= state[t]
            bits.append(state[-1])
            state = [feedback] + state[:-1]

        bits = np.array(bits)
        print(f"[DEBUG] order={order}, length={length}, oversample={oversample}, total_samples={length * oversample}")
        print("Bits:", bits[:50])
        print("Unique bit values:", np.unique(bits))

        waveform = np.repeat(bits, oversample)
        time = np.arange(len(waveform)) / sampling_frequency
        self.logger._log_command(command="generate PRBS wave", duration_ms=None, response = "Successfully generated")

        return time, waveform
    

    def generate_noise(self, varience, duration):
        varience = varience
        duration = duration * 1e-9

        t = np.arange(0, duration, 1 / self.sampling_frequency)
        waveform = np.random.normal(0, np.sqrt(self.varience), len(t))
        self.logger._log_command(command="generate noise wave", duration_ms=None, response = "Successfully generated")
        return t, waveform
    
    
    def compute_fft(self, w, **kwargs):
        """
        Compute FFT of signal and return shifted frequency axis.
        Args:
            w (ndarray): input waveform
            sampling_freq (float): sampling frequency in Hz (default 8 GHz)
        """
        if kwargs.get("sampling_frequency") is not None:
            sampling_frequency = kwargs.get("sampling_frequency")
        else:
            sampling_frequency = self.sampling_frequency
        N = len(w)
        # FFT
        x = fftshift(fft(w))
        P_W = (np.abs(x) / N) ** 2 /(50 *2)  # normalize magnitude
        P_dBm = 10 * np.log10(P_W / 1e-3)  # reference 1 mW    
        # Frequency axis
        freq = fftshift(fftfreq(N, d=1/sampling_frequency)) / 1e9 # convert to GHz
        return freq, P_dBm
    
    def compute_spectrogram(self,data, **kwargs):
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
        if kwargs.get("sampling_frequency") is not None:
            sampling_frequency = kwargs.get("sampling_frequency")
        else:
            sampling_frequency = self.sampling_frequency

        nperseg = min(64, len(data))
        noverlap = nperseg // 2 
        f_spec, t_spec, Sxx = signal.spectrogram(data,fs=sampling_frequency,nperseg=nperseg,noverlap=noverlap,window='hann')
        df = f_spec[1] - f_spec[0] #Freq bin width ,Ar
        Sxx_bin_W = (Sxx / 50) * df # convert Psd into power per bin in watts asssuming 50 ohm system
        Sxx_bin_dBm =10*np.log10(Sxx_bin_W * 1e3) # convert to dBm
        return f_spec, t_spec, Sxx_bin_dBm