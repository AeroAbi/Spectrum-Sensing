import sys
import os
import csv
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QFileDialog, QFormLayout,
    QMessageBox, QCheckBox, QScrollArea, QSpinBox, QDoubleSpinBox

)

from PyQt5.QtGui import QPixmap, QColor, QPainter,QIntValidator,QDoubleValidator
from PyQt5.QtCore import QSize
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from config_loader import load_config
# from ADQ14 import ADQ14Reader  # Your ADQ class
from GUI_Handler import GUI_Handler
from datetime import datetime



CONFIG = load_config()

class StatusLight(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.set_connected(False)

    def set_connected(self, connected):
        pixmap = QPixmap(self.size())
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        color = QColor(0, 255, 0) if connected else QColor(0, 100, 0)
        painter.setBrush(color)
        painter.setPen(QColor("black"))
        painter.drawEllipse(0, 0, 20, 20)
        painter.end()
        self.setPixmap(pixmap)

class SS_GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.combined_params_per_wave ={}
        self.setWindowTitle("Spectrum Sensing Data Collection")
        self.setGeometry(100, 100, 1000, 600)

        self.params = { "channel": {"params":{"data": 1,  "rf_reference": 2}}, # direct channel number 1 or 2
                        "reference_data_choice": 0, #index of choice in choice list 
                        "awg_ip": "192.168.0.112", 
                        "num_samples": 2500, 
                        "sampling_freq": 25e9,
                        "signal_duration": 6000E-9,
                        "awg_delay": 10e-4,
                        "adq_num_samples": 6000, 
                        "adq_sampling_freq": 1e9,
                        "data_save_location": "C:\\Users\\USER\\Desktop\\Abinaya\\Data",
                        "waveform": {"type": None, "params": {}},
                        "single_channel_mode": True,
                        "amplitude": {"params": {"start_amp": 0.25, "stop_amp": 0.25, "step_amp": 0.025}},
                        "adq_channel": {'params': {"data": 2, "rf_reference": 0}}, # index of channel from ['A', 'B', 'C', 'D']
                        "adq_visualization": "Spect", #"Spect" or "FFT" 
                        "stretch_factor": None, #TODO: add UI elements once Mandeep/Ritu do simulations & prepare code
                        }

        self.handler = GUI_Handler(self)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab_widgets = {}

        tabs_list = {"Settings": self.init_settings_tab,
                     "AWG": self.init_awg_tab,
                     "ADQ14": self.init_adq14_tab,
                     "Run": self.init_run_tab}
        for tab_name in tabs_list.keys():
            widget = QWidget()
            self.tabs.addTab(widget, tab_name)
            self.tab_widgets[tab_name] = widget
 
        for tab_name, tab_method in tabs_list.items():
            setattr(self, f"{tab_name.lower().replace(' ', '_')}_tab", self.tab_widgets[tab_name])
            tab_method()
    
    
    def _update_params(self, name, value, **kwargs):
        if kwargs.get("param_name") is not None:
            self.params[kwargs.get("param_name")]["params"][name] = value
        else:
            self.params[name] = value


    def init_settings_tab(self):
        layout = QHBoxLayout()
        side_panel = QVBoxLayout()
        main_panel = QVBoxLayout()

        self.status_light = StatusLight()
        side_panel.addWidget(self.status_light)

        # --- Settings Group: Samples, Sampling Freq, Data Save Location ---
        settings_group = QGroupBox("Acquisition Settings")
        settings_form = QFormLayout()
        # Signal Duration
        self.signal_duration_inp = QDoubleSpinBox()
        self.signal_duration_inp.setRange(1, 10000)
        self.signal_duration_inp.setDecimals(4)
        self.signal_duration_inp.setSingleStep(10)
        self.signal_duration_inp.setValue(self.params["signal_duration"]* 1e9)
        self.signal_duration_inp.valueChanged.connect(lambda val: (self._update_params("signal_duration", val/1e9),
                                      self._update_params("num_samples", int(val * self.params["sampling_freq"]))))
                                    #   self.update_trigger_title()))
        settings_form.addRow("Signal Duration (ns):", self.signal_duration_inp)
        # Sampling Frequency
        awg_sampling_freq_inp = QDoubleSpinBox()
        awg_sampling_freq_inp.setRange(1, 100)
        awg_sampling_freq_inp.setDecimals(0)
        awg_sampling_freq_inp.setSingleStep(0.01)
        awg_sampling_freq_inp.setValue(self.params["sampling_freq"]/1e9)
        awg_sampling_freq_inp.valueChanged.connect(lambda val:( self._update_params("sampling_freq", val*1e9),
                                                                self._update_params("num_samples", int(val * self.params["signal_duration"]))))
        settings_form.addRow("AWG Sampling Frequency (GHz):", awg_sampling_freq_inp)
        # AWG Delay
        self.awg_delay_inp = QDoubleSpinBox()
        self.awg_delay_inp.setRange(0, 1000)
        self.awg_delay_inp.setDecimals(4)
        self.awg_delay_inp.setSingleStep(10)
        self.awg_delay_inp.setValue(self.params["awg_delay"]*1e9)
        self.awg_delay_inp.valueChanged.connect(lambda val: self._update_params("awg_delay", val/1e9))
        # ADQ Sampling Frequency
        adq_sampling_freq_inp = QDoubleSpinBox()
        adq_sampling_freq_inp.setRange(1, 100)
        adq_sampling_freq_inp.setDecimals(0)
        adq_sampling_freq_inp.setSingleStep(0.01)
        adq_sampling_freq_inp.setValue(self.params["adq_sampling_freq"]/1e9)
        adq_sampling_freq_inp.valueChanged.connect(lambda val:( self._update_params("adq_sampling_freq", val*1e9),
                                                                self._update_params("adq_num_samples", int(val * self.params["signal_duration"]))))
        settings_form.addRow("ADQ Sampling Frequency (GHz):", adq_sampling_freq_inp)
        # Data save location
        data_save_layout = QHBoxLayout()
        self.data_save_path = QLineEdit(self.params["data_save_location"])
        self.data_save_path.setReadOnly(True)
        self.browse_save_path_btn = QPushButton("Browse")
        data_save_layout.addWidget(self.data_save_path)
        data_save_layout.addWidget(self.browse_save_path_btn)
        settings_form.addRow("Data Save Location:", data_save_layout)
        settings_group.setLayout(settings_form)
        side_panel.addWidget(settings_group)


        # --- Connection Group: IP + Connect/Disconnect ---
        connection_group = QGroupBox("AWG Connection")
        connection_layout = QVBoxLayout()
        ip_form = QFormLayout()
        self.ip_input = QLineEdit(self.params["awg_ip"])
        self.ip_input.textChanged.connect(lambda text: self._update_params("awg_ip", text))
        ip_form.addRow("AWG IP Address:", self.ip_input)
        connection_layout.addLayout(ip_form)
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)
        connection_layout.addLayout(btn_layout)
        connection_group.setLayout(connection_layout)
        side_panel.addWidget(connection_group)

        # --- ADQ14 Connection Group: IP + Connect/Disconnect ---
        adq14_connection_group = QGroupBox("ADQ14 Connection")
        adq14_connection_layout = QVBoxLayout()
        adq14_btn_layout = QHBoxLayout()
        self.adq14_connect_btn = QPushButton("Connect")
        self.adq14_disconnect_btn = QPushButton("Disconnect")
        adq14_btn_layout.addWidget(self.adq14_connect_btn)
        adq14_btn_layout.addWidget(self.adq14_disconnect_btn)
        adq14_connection_layout.addLayout(adq14_btn_layout)
        adq14_connection_group.setLayout(adq14_connection_layout)
        side_panel.addWidget(adq14_connection_group)

        # Connect button signals for ADQ14    
        self.adq14_connect_btn.clicked.connect(self.handler.handle_adq14_connect)
        self.adq14_disconnect_btn.clicked.connect(self.handler.handle_adq14_disconnect)


        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        main_panel.addWidget(QLabel("SCPI Command Log"))
        main_panel.addWidget(self.log_box)

        layout.addLayout(side_panel, 1)
        layout.addLayout(main_panel, 3)
        self.settings_tab.setLayout(layout)

        # Connect button signals
        # self.num_samples_inp.textChanged.connect(self.update_trigger_title)
        self.connect_btn.clicked.connect(self.handler.handle_connect)
        self.disconnect_btn.clicked.connect(self.handler.handle_disconnect)
        self.browse_save_path_btn.clicked.connect(self.browse_data_save_location)

    def browse_data_save_location(self):
        path = QFileDialog.getExistingDirectory(self, "Select Data Save Location", os.getcwd())
        if path:
            self.data_save_path.setText(path)
            self._update_params("data_save_location", path)

    # --- Acquisition Device Selection --- #updated-30apr
        device_group = QGroupBox("Acquisition Device")
        device_layout = QFormLayout()

        self.device_selector = QComboBox()
        self.device_selector.addItems(["ADQ14", "Keysight Oscilloscope"])
        self.device_selector.setCurrentText(self.params["acquisition_device"])

        self.device_selector.currentTextChanged.connect(lambda text: self._update_params("acquisition_device", text))

        device_layout.addRow("Select Device:", self.device_selector)
        device_group.setLayout(device_layout)
        # side_panel.addWidget(device_group)        
    
    # --- Keysight Oscilloscope Connection Group ---
        keysight_group = QGroupBox("Keysight Oscilloscope Connection")
        keysight_layout = QVBoxLayout()

        keysight_ip_form = QFormLayout()
        self.keysight_ip_input = QLineEdit(self.params["keysight_ip"])
        self.keysight_ip_input.textChanged.connect(lambda text: self._update_params("keysight_ip", text))
        keysight_ip_form.addRow("Keysight IP:", self.keysight_ip_input)

        keysight_btn_layout = QHBoxLayout()
        self.keysight_connect_btn = QPushButton("Connect")
        self.keysight_disconnect_btn = QPushButton("Disconnect")

        keysight_btn_layout.addWidget(self.keysight_connect_btn)
        keysight_btn_layout.addWidget(self.keysight_disconnect_btn)

        keysight_layout.addLayout(keysight_ip_form)
        keysight_layout.addLayout(keysight_btn_layout)
        keysight_group.setLayout(keysight_layout)

        # side_panel.addWidget(keysight_group)
                

    def init_awg_tab(self):
        layout = QHBoxLayout()
        side_panel = QVBoxLayout()
        main_panel = QVBoxLayout()

        # --- Data/Reference Channel Selection ---
        channel_select_group = QGroupBox("Channel Assignment")
        channel_select_layout = QFormLayout()
        data_channel_dropdown = QComboBox()
        data_channel_dropdown.addItems(["Channel 1", "Channel 2"])
        reference_channel_dropdown = QComboBox()
        reference_channel_dropdown.addItems(["Channel 1", "Channel 2"])
        single_channel_option = QCheckBox("Use without Reference Channel")
        data_channel_dropdown.setCurrentIndex(0)
        reference_channel_dropdown.setCurrentIndex(1)
        channel_select_layout.addRow("Data Channel:", data_channel_dropdown)
        channel_select_layout.addRow("Reference Channel:", reference_channel_dropdown)
        channel_select_layout.addRow("", single_channel_option)
        channel_select_group.setLayout(channel_select_layout)
        side_panel.addWidget(channel_select_group)


        def sync_channel_dropdowns():
            data_idx = data_channel_dropdown.currentIndex()
            ref_idx = 1 - data_idx
            reference_channel_dropdown.blockSignals(True)
            reference_channel_dropdown.setCurrentIndex(ref_idx)
            reference_channel_dropdown.blockSignals(False)
            self._update_params("data", data_idx + 1, param_name="channel")
            self._update_params("reference", ref_idx + 1, param_name="channel")

        def sync_reference_dropdown():
            ref_idx = reference_channel_dropdown.currentIndex()
            data_idx = 1 - ref_idx
            data_channel_dropdown.blockSignals(True)
            data_channel_dropdown.setCurrentIndex(data_idx)
            data_channel_dropdown.blockSignals(False)
            self._update_params("data", data_idx + 1, param_name="channel")
            self._update_params("reference", ref_idx + 1, param_name="channel")
        data_channel_dropdown.currentIndexChanged.connect(sync_channel_dropdowns)
        reference_channel_dropdown.currentIndexChanged.connect(sync_reference_dropdown)
        single_channel_option.stateChanged.connect(
            lambda state: (
                reference_channel_dropdown.setEnabled(not bool(state)),
                self._update_params("channel", {"data":data_channel_dropdown.currentIndex() + 1}),
                self._update_params("single_channel_mode", bool(state)),
                ref_select_group.setHidden(not bool(state))
            )
        )

        # --- Reference Data Type Selection ---
        ref_select_group = QGroupBox("Reference Selection")
        ref_select_layout = QFormLayout()
        reference_signal_dropdown = QComboBox()
        reference_signal_dropdown.addItems(["Same as Data", "Data stretched by stretch factor"])
        reference_signal_dropdown.setCurrentIndex(self.params["reference_data_choice"])
        reference_signal_dropdown.currentIndexChanged.connect(lambda val: self._update_params("reference_data_choice", val))
        ref_select_layout.addRow("Reference Signal:", reference_signal_dropdown)
        ref_select_group.setLayout(ref_select_layout)
        side_panel.addWidget(ref_select_group)
        ref_select_group.setHidden(self.params["single_channel_mode"])

        # ---- Amplitude Parameters group ----
        common_param_group = QGroupBox("Amplitude (Vpp)")
        common_param_form = QFormLayout()

        start_amp = QDoubleSpinBox()
        start_amp.setRange(0.1, 0.7)
        start_amp.setDecimals(4)
        start_amp.setSingleStep(0.01)
        start_amp.setValue(0.25)
        start_amp.valueChanged.connect(lambda val: self._update_params("start_amp", val, param_name="amplitude"))

        stop_amp = QDoubleSpinBox()
        stop_amp.setRange(0.1, 0.7)
        stop_amp.setDecimals(4)
        stop_amp.setSingleStep(0.01)
        stop_amp.setValue(0.25)
        stop_amp.valueChanged.connect(lambda val: self._update_params("stop_amp", val, param_name="amplitude"))

        step_amp = QDoubleSpinBox()
        step_amp.setRange(0.0, 0.6)
        step_amp.setDecimals(4)
        step_amp.setSingleStep(0.01)
        step_amp.setValue(0.25)
        step_amp.valueChanged.connect(lambda val: self._update_params("step_amp", val, param_name="amplitude"))

        common_param_form.addRow("Start Amplitude (Vpp):", start_amp)
        common_param_form.addRow("Stop Amplitude (Vpp):", stop_amp)
        common_param_form.addRow("Step Amplitude (Vpp):", step_amp)

        common_param_group.setLayout(common_param_form)
        common_param_group.setVisible(True)
        side_panel.addWidget(common_param_group)
        

        # ---- Waveform selection ----
        waveform_group = QGroupBox()
        waveform_layout = QHBoxLayout()
        waveform_label = QLabel("Select Waveform:")
        self.waveform_selector = QComboBox()
        self.waveform_selector.addItems(CONFIG["waveforms"]["options"])
        # self.waveform_selector.currentTextChanged.connect(lambda text: self.handler.update_waveform_inputs(text, 1))
        generate_btn = QPushButton("Generate Waveform")
        generate_btn.clicked.connect(lambda: self.handler.handle_generate_waveform2())
        waveform_layout.addWidget(waveform_label)
        waveform_layout.addWidget(self.waveform_selector)
        waveform_layout.addWidget(generate_btn)
        waveform_group.setLayout(waveform_layout)
        side_panel.addWidget(waveform_group)
        

        # --- Waveform parameter definitions ---
        self.waveform_param_defs = {
            "Sine": [
                ("start_freq", "Start Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("stop_freq", "Stop Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("step_freq", "Step Frequency (GHz):", None),
            ],
            "PRBS": [
                ("start_order", "Start Order:", None),
                ("stop_order", "Stop Order:", None),
                ("step_order", "Step Order:", None),
                ("prbs_repetition_rate", "Repetition Rate", None),
            ],
            "Noise": [
                ("start_variance", "Start Variance (Hz):", None),
                ("stop_variance", "Stop Variance (Hz):", None),
                ("step_variance", "Step Variance (Hz):", None),
                ("duration", "Duration (ns):", None),
            ],
            "LFM": [
                ("start_center_frequency", "Starting Center Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("stop_center_frequency", "Stoping Center Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("step_center_frequency", "Step Center Frequency (GHz):", None),
                ("pulse_width", "Pulse width (ns):", None),
                ("bandwidth", "Bandwidth (GHz):", None),
            ],
            ##updated##
            "StepLFM": [
                # ("start_frequency", "Starting Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                # ("stop_frequency", "Stoping Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                # ("step_frequency", "Step Frequency (GHz):", None),
                # ("dwell_time", "Dwell time (ns):", None),
                ("Start_frequency_initial", "Starting Initial Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("Start_frequency_final", "Starting Final Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("Start_frequency_step", "Starting Step Frequency (GHz):", None),
                ("dwell_time", "Dwell time (ns):", None),

                ("StepLFM_frequency", "StepLFM Step Frequency (GHz):", QDoubleValidator(0.0, 4.0, 4)),
                ("StepLFM_Nstep", "Step LFM Number of Step(N):", None)
            ],
        }

        # --- Parameter widgets storage ---
        param_widgets = {}

        def display_waveform_params(waveform):
            self._update_params("waveform", {"type": waveform, "params": {}})
            # Remove old widgets
            while self.param_layout.count():
                item = self.param_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            # Add new widgets
            param_widgets[waveform] = {}
            # print(f"Displaying params for {waveform}: {self.waveform_param_defs.get(waveform, [])}")
            for name, label, validator in self.waveform_param_defs.get(waveform, []):
                w = QLineEdit()
                if validator:
                    w.setValidator(validator)
                self.param_layout.addRow(label, w)
                param_widgets[waveform][name] = w
                param_widgets[waveform][name].textChanged.connect(lambda val, name=name: self._update_params(name, val, param_name='waveform'))
            self.param_group.setVisible(bool(self.waveform_param_defs.get(waveform)))

        def get_current_waveform_params(self):
            waveform = self.waveform_selector.currentText()
            widgets = param_widgets.get(waveform, {})
            return {name: widget.text() for name, widget in widgets.items()}

        # --- Parameter group for dynamic display ---
        self.param_group = QGroupBox("Waveform Parameters")
        self.param_layout = QFormLayout()
        self.param_group.setLayout(self.param_layout)
        side_panel.addWidget(self.param_group)
        self.param_group.setVisible(False)

        # Connect waveform selector to dynamic param display
        self.waveform_selector.currentTextChanged.connect(display_waveform_params)
        
        # Create the matplotlib view
        plot_group = QGroupBox("Sample waveform")
        plot_layout = QHBoxLayout()

        # Matplotlib figure and canvas: 2 subplots (time and FFT)
        self.awg_fig = Figure(figsize=(5, 4))
        self.awg_canvas = FigureCanvas(self.awg_fig)
        plot_layout.addWidget(self.awg_canvas)

        plot_group.setLayout(plot_layout)
        main_panel.addWidget(plot_group)

        layout.addLayout(side_panel, 1)
        layout.addLayout(main_panel, 3)
        self.awg_tab.setLayout(layout)

        
    
    def init_combined_waveform_tab(self):
       layout = QHBoxLayout()

       # ===== SIDE PANEL (scrollable) =====
       side_widget = QWidget()
       side_panel = QVBoxLayout(side_widget)   # create layout and attach to widget

       scroll_area = QScrollArea()
       scroll_area.setWidgetResizable(True)
       scroll_area.setWidget(side_widget)      # connect side_widget to scroll

       # ---- Channels ----
       channel_box = QGroupBox("Select Channels")
       ch_layout = QHBoxLayout()
       self.ch1_cb = QCheckBox("Channel 1")
       self.ch2_cb = QCheckBox("Channel 2")
       
       ch_layout.addWidget(self.ch1_cb)
       ch_layout.addWidget(self.ch2_cb)
       channel_box.setLayout(ch_layout)
       side_panel.addWidget(channel_box)

       # ---- Waveform controls ----
       self.wave_boxes = []
       self.dropdown_boxes = []
       self.param_groups = []

       for i in range(5):
           cb = QCheckBox(f"Waveform {i+1}")
           cb.stateChanged.connect(self.toggle_dropdown)
           self.wave_boxes.append(cb)

           dropdown = QComboBox()
           dropdown.addItems(["Select", "Sine", "PRBS", "LFM", "Step_LFM", "Noise"])
           dropdown.currentIndexChanged.connect(self.show_parameters)
           dropdown.setVisible(False)
           self.dropdown_boxes.append(dropdown)

           param_group = QGroupBox(f"Parameters for Waveform {i+1}")
           param_group.setVisible(False)
           param_layout = QFormLayout()
           param_group.setLayout(param_layout)
           self.param_groups.append(param_group)

           side_panel.addWidget(cb)
           side_panel.addWidget(dropdown)
           side_panel.addWidget(param_group)

       # ---- Common parameters ----
       self.ch1_cb.stateChanged.connect(self.handler.toggle_ch_bx)
       self.ch2_cb.stateChanged.connect(self.handler.toggle_ch_bx)
       num_samples_group = QGroupBox("Common Parameters")
       num_samples_layout = QFormLayout()

       self.num_samples = QLineEdit()
       setattr(self, f'combined_start_amp', QLineEdit())
       setattr(self, f'combined_stop_amp', QLineEdit())
       setattr(self, f'combined_step_amp', QLineEdit())
       

       num_samples_layout.addRow("Number of Samples:", self.num_samples)
       num_samples_layout.addRow("start amplitude", getattr(self, f'combined_start_amp'))
       num_samples_layout.addRow("stop amplitude", getattr(self, f'combined_stop_amp'))
       num_samples_layout.addRow("step amplitude", getattr(self, f'combined_step_amp'))
       num_samples_group.setLayout(num_samples_layout)
       side_panel.addWidget(num_samples_group)

       # Combined upload checkbox group
       self.combineduploadcheckgroup = QGroupBox("Upload Waveform")
       uploadlayout = QHBoxLayout()
       self.combined_upload_check_bx = QCheckBox("Upload Waveform to AWG")
       self.combined_upload_check_bx.stateChanged.connect(lambda: self.handler.toggle_upload_check('combined'))
       uploadlayout.addWidget(self.combined_upload_check_bx)
       self.combineduploadcheckgroup.setLayout(uploadlayout)
       side_panel.addWidget(self.combineduploadcheckgroup)

       # Combined upload file group
       self.combineduploadgroup = QGroupBox("Upload Waveform File")
       uploadfilelayout = QFormLayout()
       uploadbtnslayout = QHBoxLayout()
       self.combined_file_path_input = QLineEdit()
       self.combined_file_path_input.setReadOnly(True)
       self.combinedbrowsebtn = QPushButton("Browse")
       self.combineduploadbtn = QPushButton("Upload")
       uploadfilelayout.addRow("Waveform File Path:", self.combined_file_path_input)
       uploadbtnslayout.addWidget(self.combinedbrowsebtn)
       uploadbtnslayout.addWidget(self.combineduploadbtn)
       uploadfilelayout.addRow(uploadbtnslayout)
       self.combineduploadgroup.setLayout(uploadfilelayout)
       self.combineduploadgroup.setEnabled(False)
       side_panel.addWidget(self.combineduploadgroup)


       # ---- Generate, run, and abort buttons ----
       self.generate_wave_group = QGroupBox()
       generate_wave_layout = QFormLayout()
       run_abrt_layout = QHBoxLayout()
       generate_wave_btn = QPushButton(CONFIG['buttons']['Generate_waveform']['label'])
       run_btn = QPushButton(CONFIG["buttons"]['run']['label'])
       abrt_btn = QPushButton(CONFIG['buttons']['abort']['label'])
       
       generate_wave_layout.addRow(generate_wave_btn)
       run_abrt_layout.addWidget(run_btn)
       run_abrt_layout.addWidget(abrt_btn)
       generate_wave_layout.addRow(run_abrt_layout)
       self.generate_wave_group.setLayout(generate_wave_layout)
       side_panel.addWidget(self.generate_wave_group)

       side_panel.addStretch()

       main_panel = QVBoxLayout()
       plot_group = QGroupBox("Combined Plot")
       plot_layout = QVBoxLayout()

       self.combfig = Figure(figsize=(5, 4))
       self.combcanvas = FigureCanvas(self.combfig)
       plot_layout.addWidget(self.combcanvas)

       self.combrefreshbtn = QPushButton("Refresh Graph")
       plot_layout.addWidget(self.combrefreshbtn)

       plot_group.setLayout(plot_layout)
       main_panel.addWidget(plot_group)


    #    # ===== PLOT PANEL =====
    #    main_panel = QVBoxLayout()
    #    plot_group = QGroupBox("Sample waveform")
    #    plot_layout = QHBoxLayout()
    #    self.plot_view = QWebEngineView()
    #    plot_layout.addWidget(self.plot_view)
    #    plot_group.setLayout(plot_layout)
    #    main_panel.addWidget(plot_group)

       # ---- Connect buttons ----
       self.combinedbrowsebtn.clicked.connect(lambda: self.handler.handle_browse_file('combined'))
       self.combineduploadbtn.clicked.connect(lambda: self.handler.handle_upload_waveform(self.combined_file_path_input.text().strip(),channel=1, combine=True))
       generate_wave_btn.clicked.connect(lambda: self.handler.handle_combined_waveform(channel= self.select_run_channel()))
       run_btn.clicked.connect(lambda:self.handler.run( channel=1,combine=True))
       abrt_btn.clicked.connect(lambda:self.handler.handle_abort(channel=self.select_run_channel(),combine=True))
       #self.combrefreshbtn.clicked.connect(lambda: self.handler.refreshplot("combined"))
       self.sweeptimegroup_combined=QGroupBox("sweep Time Control")
       # ===== COMBINE =====
       layout.addWidget(scroll_area, 1)
       layout.addLayout(main_panel, 3)  # ✅ main_panel is a layout, not a widget
       self.combined_waveform_tab.setLayout(layout)
    
    def init_adq14_tab(self):
        layout = QHBoxLayout()
        sidepanel = QVBoxLayout()
        mainpanel = QVBoxLayout()
        
        # # ADQ Settings Group (like channel1 waveform selector)
        # adqsettingsgroup = QGroupBox("ADQ Settings")
        # settingsform = QFormLayout()
        # self.adqinterpolation = QLineEdit("1")
        # settingsform.addRow("Interpolation:", self.adqinterpolation)
        # adqsettingsgroup.setLayout(settingsform)
        # sidepanel.addWidget(adqsettingsgroup)
        
        # Update Waveform Button
        # self.adqupdatebtn = QPushButton("Update Waveform")
        # sidepanel.addWidget(self.adqupdatebtn)
        
        # Channel Select Dropdowns: Data, Reference, N Divided (with sync logic)
        channelgroup = QGroupBox("Channel Select")
        channellayout = QFormLayout()
        # Data Channel
        self.adq_data_channel = QComboBox()
        self.adq_data_channel.addItems(["A", "B", "C", "D"])
        channellayout.addRow(QLabel("Data Channel:"), self.adq_data_channel)
        # Reference Channel
        self.adq_reference_channel = QComboBox()
        self.adq_reference_channel.addItems(["A", "B", "C", "D"])
        channellayout.addRow(QLabel("Reference Channel:"), self.adq_reference_channel)
        # N Divided Channel with enable checkbox
        ndiv_layout = QHBoxLayout()
        self.adq_ndiv_channel = QComboBox()
        self.adq_ndiv_channel.addItems(["A", "B", "C", "D"])
        self.adq_ndiv_channel.setEnabled(False)
        self.adq_ndiv_enable = QCheckBox("Enable N Divided")
        ndiv_layout.addWidget(self.adq_ndiv_channel)
        ndiv_layout.addWidget(self.adq_ndiv_enable)
        ndiv_widget = QWidget()
        ndiv_widget.setLayout(ndiv_layout)
        channellayout.addRow(QLabel("N Divided Channel:"), ndiv_widget)
        channelgroup.setLayout(channellayout)
        sidepanel.addWidget(channelgroup)

        self.adq_data_channel.setCurrentIndex(self.params['adq_channel']['params']['data'])

        # --- Sync logic for mutual exclusion ---
        def sync_adq_channels(changed):
            # Get all current selections
            data_idx = self.adq_data_channel.currentIndex()
            ref_idx = self.adq_reference_channel.currentIndex()
            ndiv_enabled = self.adq_ndiv_enable.isChecked()
            ndiv_idx = self.adq_ndiv_channel.currentIndex() if ndiv_enabled else None

            # Build available indices
            all_indices = set(range(self.adq_data_channel.count()))

            # If Data changed
            if changed == 'data':
                # Reference and N Divided must not match Data
                if ref_idx == data_idx:
                    # Pick next available
                    for idx in all_indices - {data_idx}:
                        self.adq_reference_channel.setCurrentIndex(idx)
                        ref_idx = idx
                        break
                if ndiv_enabled and ndiv_idx == data_idx:
                    for idx in all_indices - {data_idx, ref_idx}:
                        self.adq_ndiv_channel.setCurrentIndex(idx)
                        break
            # If Reference changed
            elif changed == 'reference':
                if data_idx == ref_idx:
                    for idx in all_indices - {ref_idx}:
                        self.adq_data_channel.setCurrentIndex(idx)
                        data_idx = idx
                        break
                if ndiv_enabled and ndiv_idx == ref_idx:
                    for idx in all_indices - {data_idx, ref_idx}:
                        self.adq_ndiv_channel.setCurrentIndex(idx)
                        break
            # If N Divided changed
            elif changed == 'ndiv':
                if ndiv_enabled:
                    if ndiv_idx == data_idx:
                        for idx in all_indices - {data_idx, ref_idx}:
                            self.adq_ndiv_channel.setCurrentIndex(idx)
                            ndiv_idx = idx
                            break
                    if ndiv_idx == ref_idx:
                        for idx in all_indices - {data_idx, ref_idx}:
                            if idx != ndiv_idx:
                                self.adq_ndiv_channel.setCurrentIndex(idx)
                                break

        self.adq_reference_channel.currentIndexChanged.connect(lambda _: (sync_adq_channels('reference'), self._update_params('reference', self.adq_reference_channel.currentIndex(), param_name='adq_channel')))
        self.adq_ndiv_channel.currentIndexChanged.connect(lambda _: (sync_adq_channels('ndiv'), self._update_params('ndiv', self.adq_ndiv_channel.currentIndex() if self.adq_ndiv_enable.isChecked() else None, param_name='adq_channel')))
        self.adq_ndiv_enable.stateChanged.connect(lambda _: sync_adq_channels('ndiv'))
        self.adq_data_channel.currentIndexChanged.connect(lambda _: self._update_params('data', self.adq_data_channel.currentIndex(), param_name='adq_channel'))
        
        # Signal Processing Checkboxes
        sigprocgroup = QGroupBox("Signal Processing")
        sigproclayout = QVBoxLayout()
        sigprocoptions = QComboBox()
        sigprocoptions.addItems(['FFT', 'Spect'])
        sigprocoptions.setCurrentText(self.params["adq_visualization"])
        sigprocoptions.currentTextChanged.connect(lambda val:self._update_params("adq_visualization", val))
        sigproclayout.addWidget(sigprocoptions)
        sigprocgroup.setLayout(sigproclayout)
        sidepanel.addWidget(sigprocgroup)
        
        sidepanel.addStretch()
        
        # Plot Area 
        plotgroup = QGroupBox("ADQ Plot")
        plotlayout = QHBoxLayout()
        self.adqfig = Figure(figsize=(5, 4))
        self.adqcanvas = FigureCanvas(self.adqfig)
        plotlayout.addWidget(self.adqcanvas)
        plotgroup.setLayout(plotlayout)
        mainpanel.addWidget(plotgroup)
        
        layout.addLayout(sidepanel, 1)
        layout.addLayout(mainpanel, 3)
        self.adq14_tab.setLayout(layout)
        # self.adqupdatebtn.clicked.connect(lambda: self.handler.handleadqupdate())


    def init_run_tab(self):
        layout = QHBoxLayout()
        side_panel = QVBoxLayout()
        main_panel = QVBoxLayout()

        # Run group
        run_group = QGroupBox()
        run_layout = QFormLayout()
        run_btn = QPushButton("Run")
        abort_btn = QPushButton("Abort")
        run_layout.addRow(run_btn)
        run_layout.addRow(abort_btn)
        run_group.setLayout(run_layout)
        side_panel.addWidget(run_group)
        
        # run_btn.clicked.connect(lambda: self.handler.run()) #updated-30apr
        run_btn.clicked.connect(lambda: self.handler.run(acquisition_device=self.params["acquisition_device"]))
        abort_btn.clicked.connect(lambda: self.handler.handle_abort())

        #  rest of the controls can be added here as needed, for now we just put a placeholder label
        layout.addLayout(side_panel, 1)
        layout.addLayout(main_panel, 3)
        self.run_tab.setLayout(layout)

    
    def toggle_dropdown(self, state):
        for i, cb in enumerate(self.wave_boxes):
            if self.sender() == cb:
                self.dropdown_boxes[i].setVisible(cb.isChecked())
                if not cb.isChecked():
                    self.param_groups[i].setVisible(False)

    def show_parameters(self, index):
        for i, dropdown in enumerate(self.dropdown_boxes):
            if self.sender() == dropdown:
                if index == 0:
                    self.param_groups[i].setVisible(False)
                    self.combined_params_per_wave.pop(i,None)
                    return

                param_group = self.param_groups[i]
                layout = param_group.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget: widget.deleteLater()

                wf_type = dropdown.currentText()
                params_dict={"type":wf_type}

                if wf_type == "Sine":
                    self.combined_freq = QLineEdit()
                    layout.addRow("Frequency (GHz):", self.combined_freq)
                    params_dict["combined_freq"]=self.combined_freq
                elif wf_type == "PRBS":
                    self.combined_repetition_rate = QLineEdit()
                    self.combined_order = QLineEdit()
                    layout.addRow("Order:", self.combined_order)
                    layout.addRow("Repetition Rate:", self.combined_repetition_rate)

                elif wf_type == "LFM":
                    self.combined_center_freq = QLineEdit()
                    self.combined_bandwidth = QLineEdit()
                    self.combined_pulse_width = QLineEdit()
                    layout.addRow("Center Freq (GHz):", self.combined_center_freq)
                    layout.addRow("Bandwidth (GHz):", self.combined_bandwidth)
                    layout.addRow("Pulse width (ns): ", self.combined_pulse_width)
                    params_dict["combined_center_freq"]=self.combined_center_freq
                    params_dict["combined_bandwidth"]=self.combined_bandwidth
                    params_dict["combined_pulse_width"]=self.combined_pulse_width

                elif wf_type == "Step_LFM":
                    self.combined_start_freq = QLineEdit()
                    self.combined_stop_freq = QLineEdit()
                    self.combined_step_freq = QLineEdit()
                    self.combined_dwell_time = QLineEdit()
                    layout.addRow("Start Frequency (GHz):", self.combined_start_freq)
                    layout.addRow("Stop Frequency (GHz):", self.combined_stop_freq)
                    layout.addRow("Step Frequency (GHz):", self.combined_step_freq)
                    layout.addRow("Dwell Time (ns):", self.combined_dwell_time)
                    params_dict["combined_start_freq"] =self.combined_start_freq
                    params_dict["combined_stop_freq"] =self.combined_stop_freq
                    params_dict["combined_step_freq"] =self.combined_step_freq
                    params_dict["combined_dwell_time"] =self.combined_dwell_time

                elif wf_type == "Noise":
                    self.combined_variance = QLineEdit()
                    #self.combined_duration = QLineEdit()
                    #layout.addRow("Duration (ns):", self.combined_duration)
                    layout.addRow("Variance:", self.combined_variance)
                self.combined_params_per_wave[i]=params_dict
                param_group.setVisible(True)

    def select_run_channel(self):
        state_1 = self.ch1_cb.isChecked()
        state_2 = self.ch2_cb.isChecked()
        if state_1 == True:
            channel = 1
            return channel
        if state_2 == True:
            channel = 2
            return channel

    def update_trigger_title(self):
        t_last = self.handler.compute_trigger_time()
        if t_last is None:
            self.setWindowTitle("AWG Automation GUI")
        else:
            # t_last is in seconds, convert to ns or µs as you prefer
            t_ns = t_last * 1e9
            self.setWindowTitle(f"AWG Automation GUI – use t[-1] = {t_ns:.3f} ns as your external trigger")

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SS_GUI()
    window.show()
    sys.exit(app.exec_())