import sys 
import time 
from PyQt5.QtWidgets import QProgressDialog, QApplication

class ProgressBox(QProgressDialog):
    """
    ProgressBox: A reusable progress dialog for PyQt applications.

    Displays a modal progress dialog with a progress bar and a Cancel button.
    Designed for long-running tasks to provide visual feedback and allow task cancellation.

    Parameters:
        text (str)        : Message displayed in the progress dialog.
        total_steps (int) : Maximum number of steps for the task.
        parent (QWidget)  : Optional parent widget (default: None).

    Methods:
        step(value=1)
            Increment the progress bar by the specified number of steps.
            Keeps the GUI responsive during task execution.
    """

    def __init__(self, text, total_steps, parent=None):
        super().__init__(text, "Cancel", 0, total_steps, parent)
        self.setWindowTitle("Working...")
        self.setMinimumDuration(0)  # Show immediately
        self.setValue(0)            # Start at 0
        self.setAutoClose(True)     # Close automatically when finished
        self.setAutoReset(True)     # Reset automatically if reused
        self.start_time = time.time()
        self.totalsteps = total_steps #defining timer and total steps

    def Totaltime(self):
            return time.time() - self.start_time

    def update(self, value=1):  #use updat3 - normalized
        
        current = self.value() + value
        self.setValue(current)
    
        #estimated remaining time
        elapsed = time.time() - self.start_time  #current time - start time - time completed
        percent = (current/self.totalsteps)*100   #compute percentage of completed work

        #time remaining
        if current > 0:   #current > self.start_time: 
            remain_time = (elapsed / current) * (self.totalsteps - current)      #time taken to finish 1 step * total steps left
        else:
             remain_time = 0     
        
        # #total time taken - calling time function
        Total_time = time.time() - self.start_time   

        self.setLabelText(f"Generating waveforms...\n"
                f"Total Time Taken: {self.Totaltime():.1f} sec \n"
               # f"Total Time Taken: {Total_time:.1f} sec \n"  
         f"Estimated time remaining: {remain_time:.1f} sec") 
        
        QApplication.processEvents()  # Keeps the UI responsive
        
    # -------------------------------------------------

# -------------------------------------------------
def test_progress():
    freqs = [1, 2, 3, 4, 5]  
    amps = [10, 20, 30]       
                                         #normalized input --matlab waitbar
    total_steps = len(freqs) * len(amps)
    progress = ProgressBox("Generating waveforms...", total_steps)
    progress.show()
    
    step_count = 0
    for f in freqs:
        print(f"Frequency: {f} Hz")
        for a in amps:
            print(f"   Amplitude: {a} V")
            time.sleep(0.9)  # simulate some work

            # update progress
            step_count += 1
            progress.update()
            
            # check if user pressed Cancel
    if progress.wasCanceled():
        
                print("Cancelled by user!")
                progress.close()
                return
    progress.close()
    print(f"Total Time Taken: {progress.Totaltime():.1f} sec")  #im calling the fn Total time in another fn hence i use object of current fn
    print("All tasks completed!")                               #data in self is now apssed as progress


# -------------------------------------------------
# Run the example
# -------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_progress()
    sys.exit()

# import numpy as np
# import matplotlib.pyplot as plt
# from WaveformGenerator import WaveformGenerator

# Fs = 25e9
# T = 100e-9
# Vm = 0.1
# f_signal_ghz = 0.1   # 0.1 GHz

# t = np.arange(0, T, 1/Fs)
# data = np.random.randn(len(t))

# wg = WaveformGenerator()

# time, reference = wg.sinusoidal(
#     frequency=f_signal_ghz,
#     amplitude=Vm,
#     time=t
# )

# # Time domain plot
# plt.figure()
# plt.subplot(2, 1, 1)
# plt.plot(t, data, label="Data")
# plt.plot(time, reference, label="Reference", linestyle='--')
# plt.legend()
# plt.grid()

# plt.show()
