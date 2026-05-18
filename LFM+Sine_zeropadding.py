import numpy as np
import os
import csv
import matplotlib.pyplot as plt
from WaveformGenerator_v2_trial import WaveformGenerator   # your class file




def save_waveform_to_csv(w_values, frequency, folder):
    freq_ghz = frequency / 1e9
    filename = f"SS_{freq_ghz:.1f}GHz.txt"
    full_path = os.path.join(folder, filename)

    try:
        with open(full_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Amplitude"])
            for a in w_values:
                writer.writerow([a])

            print(f"Saved waveform for {freq_ghz:.1f} GHz --> {full_path}")
            return full_path

    except Exception as e:
            print(f"Error saving CSV: {str(e)}")
            return None


# ---------------- TEST ----------------
def test_save_waveform_to_csv():

    folder = r"C:\Users\aeron\Downloads\waveforms"

    fs = 25e9
    duration = 1e-3

    wg = WaveformGenerator(sampling_frequency=fs)

    test_frequencies = [1e9]   # center frequency 

    for f in test_frequencies:

        # durations
        pad_time = 50e-9 #50ns zeropadding
        first_signal_time = 100e-9 #LFM signal duration

        # samples
        n_total = int(duration * fs)
        n_pad = int(pad_time * fs)

        # LFM
        t1, signal1 = wg.generate_lfm(center_freq_ghz=1,bandwidth_ghz=0.5,pulse_width_ns=100,duration_s=first_signal_time,phase_deg=0)
        signal1 = 250e-3 * signal1  
        n_signal1 = len(signal1)

        # Sine
        n_signal2 = n_total - (2 * n_pad) - n_signal1
        t2 = np.arange(n_signal2) / fs
        signal2 = 230e-3 * np.sin(2 * np.pi * 3e9 * t2)

        # zero padding
        zeros_start = np.zeros(n_pad)
        zeros_end = np.zeros(n_pad)

        #  waveform
        w = np.concatenate([zeros_start,signal1,signal2,zeros_end])
        t = np.arange(len(w)) / fs

        print("Total samples:", len(w))
        print("LFM samples:", len(signal1))
        print("Sine samples:", len(signal2))

    
        save_waveform_to_csv(w_values=w,frequency=f,folder=folder)

        # plot
        plt.figure(figsize=(12,4))
        plt.plot(t*1e9, w)
        plt.xlabel("Time (ns)")
        plt.ylabel("Amplitude (V)")
        plt.title("Zero Padding + LFM + Sine")
        plt.grid()
        plt.show()


# run
if __name__ == "__main__":
    test_save_waveform_to_csv()