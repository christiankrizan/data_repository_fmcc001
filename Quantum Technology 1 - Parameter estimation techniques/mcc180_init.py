"""
This init script is configured to work with the hardware setup in the Chalmers lab,
as of January 2023.

This initialization script has the following structure:

Imports and setup
1 basic imports
    Here, python modules required for the experiments are imported. This includes:
    - generic scientfic python modules (numpy, scipy, matplotlib, etc. ).
    - specific experiment modules (quantify-core, quantify-scheduler,
      superconducting_qubit_tools, etc.)
    - instrument driver classes required for the experiment (qcodes instruments and
      quantify specific instruments)
2 specify hardware configuration
    The hardware configuration contains information about the connectivity of the hardware 
    to the device, as well as hardware-specific settings (see Quantify-Scheduler documentation)
3 configure basic settings
    Here, we specify the desired data directory
4 Instantiate Instruments
    To run an experiment, we require differt kinds of instruments. See also the
    documentation of quantify-scheduler
    - Physical instruments -> these are the QCoDeS drivers for corresponding to the
      instruments in the setup.
    - Hardware abstraction layer -> the InstrumentCoordinator and ICcomponents
      responsible for providing a hardware agnostic interface to the experiment flow.
    - Utility instruments -> measurement control and various monitoring instruments.
    - Configuration management instruments -> QuantumDevice and the DeviceElements
5 Loading settings from previous experiments (data) onto instruments
"""
# pylint: disable=wrong-import-position
# pylint: disable=unused-import
# pylint: disable=wrong-import-order
# pylint: disable=(django-not-configured)

############################################
# 1. Basic imports
############################################


# 1.1 Generic python imports

import time

# for benchmarking purposes
t0 = time.time()

# pylint: disable=unused-import
import os
import sys
import json
import inspect
import socket
from pathlib import Path
from importlib import reload
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from IPython.display import display, SVG
from netCDF4 import *

# from autodepgraph import AutoDepGraph_DAG


# 1.2 experiment transmon and quantify imports

from quantify_core.utilities.experiment_helpers import load_settings_onto_instrument

from quantify_core.data.handling import (
    get_datadir,
    set_datadir,
    locate_experiment_container,
    get_latest_tuid,
)

from superconducting_qubit_tools import measurement_functions as meas
from superconducting_qubit_tools import calibration_functions as cal


# 1.3 Instrument imports


import quantify_core.measurement as mc
import quantify_core.visualization.pyqt_plotmon as pqm
from quantify_core.visualization.instrument_monitor import InstrumentMonitor

from qblox_instruments.qcodes_drivers.spi_rack import SpiRack

from quantify_scheduler.instrument_coordinator.instrument_coordinator import (
    InstrumentCoordinator,
)
from quantify_scheduler.instrument_coordinator.components.qblox import (
    ClusterComponent,
)

from superconducting_qubit_tools.device_under_test.quantum_device import QuantumDevice
from superconducting_qubit_tools.device_under_test.sudden_nz_edge import (
    SuddenNetZeroEdge,
)
from superconducting_qubit_tools.device_under_test.transmon_element import (
    BasicTransmonElement,
)

from qblox_instruments import Cluster

from qcodes.instrument.base import Instrument
from superconducting_qubit_tools.instruments import USB_SA124B as usb

t1 = time.time()
print(f"Finished basic imports {t1-t0:.2f} s")

############################################
# 2. Specify hardware configuration
############################################
# define the hardware configuration file for the setup [Note this format will be changed by Q1 2023!]
# Describes the connectivity from the quantum device to the control hardware.

RO_settings =  {'LO' : 5800000000, 'off_I': 0, 'off_Q': 0}

hardware_cfg = {
   "backend": "quantify_scheduler.backends.qblox_backend.hardware_compile",
   "clusterA": {
      "ref": "internal",
      "instrument_type": "Cluster",
      "clusterA_module2": {
         "instrument_type": "QCM_RF",
         "complex_output_0": {
            "lo_freq": 5312327240.0,
            "dc_mixer_offset_I": 0,
            "dc_mixer_offset_Q": 0,
            "portclock_configs": [
               {
                  "port": "q00:mw",
                  "clock": "q00.01",
                  "mixer_amp_ratio": 1,
                  "mixer_phase_error_deg": 0
               }
            ]
         }
      },
      "clusterA_module10": {
         "instrument_type": "QRM_RF",
         "complex_output_0": {
            "lo_freq": 7197494954.0,
            "dc_mixer_offset_I": 0,
            "dc_mixer_offset_Q": 0,
            "portclock_configs": [
               {
                  "port": "q00:res",
                  "clock": "q00.ro",
                  "mixer_amp_ratio": 1,
                  "mixer_phase_error_deg": 0
               }
            ]
         }
      }
   }
}


#############################
# 3 configure basic settings
#############################

# set data directory
set_datadir(os.path.join(Path.home(), "quantify-data"))
print(f"\nData directory set to: {get_datadir()}\n")


#############################
# 4 Instantiate Instruments
#############################

# physical instruments
#############################

print("connecting to qblox-cluster-MM.")
cluster0 = Cluster("clusterA", "192.0.2.142")
print("CMM system status is \n", cluster0.get_system_state())
print("correctly connected to qblox-cluster-MM.\n")

# Reset
cluster0.reset()

# SPI_RACK_ADDR = "COM6"
# spi = SpiRack("spi", SPI_RACK_ADDR)
# spi.add_spi_module(3, "S4g")

# Signal hound spectrum analyzer.
# N.B. Comment this line if you want to use the SH GUI!
# signal_hound = usb.SignalHound_USB_SA124B("signal_hound")
# print("\n SignalHound ready")

# hardware abstraction layer
#############################

ic_cluster0 = ClusterComponent(cluster0)

instrument_coordinator = InstrumentCoordinator("instrument_coordinator")
instrument_coordinator.add_component(ic_cluster0)

# utility instruments
#############################


meas_ctrl = mc.MeasurementControl("meas_ctrl")
nested_meas_ctrl = mc.MeasurementControl("nested_meas_ctrl")
# Create the live plotting intrument which handles the graphical interface
# Two windows will be created, the main will feature 1D plots and any 2D plots will go
# to the secondary
plotmon = pqm.PlotMonitor_pyqt("plotmon")
# Connect the live plotting monitor to the measurement control
meas_ctrl.instr_plotmon(plotmon.name)

plotmon_nested = pqm.PlotMonitor_pyqt("plotmon_nested")
# Connect the live plotting monitor to the measurement control
nested_meas_ctrl.instr_plotmon(plotmon_nested.name)

# The instrument monitor will give an overview of all parameters of all instruments
insmon = InstrumentMonitor("insmon")


# Config management instruments
#############################
q0 = BasicTransmonElement("q00")

#####################################
# 5 Loading settings onto instruments
#####################################

t2 = time.time()
print(f"Finished loading instruments {t2-t0:.2f} s")

quantum_device = QuantumDevice(name="quantum_device")

quantum_device.instr_measurement_control(meas_ctrl.name)
quantum_device.instr_instrument_coordinator(instrument_coordinator.name)

quantum_device.hardware_config(hardware_cfg)

LAST_TUID = None
list_of_qubits = [q0]
for qubit in list_of_qubits:
    quantum_device.add_element(qubit)

    # # loads settings from the last datafile onto these instruments
    # try:
    #     load_settings_onto_instrument(instrument=qubit, tuid=LAST_TUID)
    # except ValueError:
    #     print(f"Failed loading {qubit}")
    #     continue

# load_settings_onto_instrument(instrument=spi, tuid=LAST_TUID)

# load_settings_onto_instrument(instrument=cluster0, tuid=LAST_TUID)

t3 = time.time()
print(f"Finished loading settings {t3-t0:.2f} s")
