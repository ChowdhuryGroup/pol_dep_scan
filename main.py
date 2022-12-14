# Original Author: Adam Fisher (July 2022)
# Modified by Liam Clink
# moving motorized thorlabs waveplate while also collecting spectra
# import utility
import numpy as np

# import thorlabs_apt_device as apt
import time

# import oceanOpticSpectrosco as spectro
import atexit
import pathlib
import argparse


class LoadFromFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        with values as f:
            contents = f.read()

        # parse arguments in the file and store them in a blank namespace
        data = parser.parse_args(contents.split(), namespace=None)
        for k, v in vars(data).items():
            # set arguments in the target namespace if they haven’t been set yet
            if getattr(namespace, k, None) is not None:
                setattr(namespace, k, v)


parser = argparse.ArgumentParser()
parser.add_argument("--motor_port", type=str, help="motor port location")
parser.add_argument(
    "--initial_angle",
    type=float,
    help="inital motor angle (degrees), background data taken at this position, must be in [0,360]",
)
parser.add_argument(
    "--final_angle", type=float, help="waveplates final angle (degrees)"
)
parser.add_argument(
    "--step",
    type=float,
    help="angular distance traveled between each spectrograph measurement (degrees)",
)
parser.add_argument("--specSN", type=str, help="spectrograph serial number")
parser.add_argument(
    "--spec_int_time", type=float, help="spectrograph integration time (msec)"
)
parser.add_argument(
    "--fname",
    type=str,
    help="file name that data will saved under (str), MUST BE A .txt file",
)
parser.add_argument(
    "--path",
    type=str,
    help="relative path to directory you would like the file saved to",
)
parser.add_argument("--file", type=open, action=LoadFromFile, help="Specify input file")
inputs = parser.parse_args()

print(inputs)


# open file, will not overwrite!
try:
    f = open(inputs.path + inputs.fname, "wb")
    atexit.register(f.close())
except FileExistsError:
    raise Exception("The selected file name already exists!")

f.write("File was created at:" + time.asctime() + "\n")
f.write("Polarizer angles [deg]:\n")

# NEED TO FIX POL POS D
pol_pos_d = np.arange(
    inputs.intial_angle, (inputs.final_angle + inputs.step), inputs.step
)  # desired polarizer positions [deg]
pol_pos_cts = np.array(
    [pol_pos_d[i] for i in range(len(pol_pos_d))]
)  # desired polarizer pos [cts]


# NOTE: ^ is just a .py file, you will need it in the same directory as this file
# NOTE: to run the above scripts you also need seabreeze package and pyserial
# NOTE: to install thorlabs_apt_device and seabreeze see line below


# currently this only works for TDC001 connected to a PRM1Z8 any other devices will have to be added in future

# build conversions for encoder cts (what APT/motor knows) to real units
# TDC001 + PRM1-Z8 factor (f) and time step (t)
t = 2048 / (6e6)  # sampling time
f = 1919.6418578623391  # encoder counts per degree factor [cts/deg], different for every stage
a = 65536.0  # extra factor to when converting velocity and acceleration

# NOTE: MUST use some sort of iteration method if you wish to use conversion functions with numpy arrays
# NOTE: this script will connect to controller will intialize and exit once it is over to prevent bad errors
# NOTE: serial number for TDC001 should be '83------'. however, adam's wasnt but stil worked, just watch out
# NOTE: need 0 <= intial and final position of polarizer <=360 [deg]
# NOTE: this assumes that the spectrograph's .getspec() program gets the same number of wavelengths each time
# NOTE: will not allow overwriting for files, if you dont change the name it was throw an error and youll have to take the data again

# print dict of important values so that they can be double checked
# list devices so you can find the controller
# things not included: motor pid/vid/serial#, any other spectrograph inputs


print("Devices visible to aptdevice: ")
print(apt.devices.aptdevice.list_devices())


# now connect to the machines
# connect to motor first as 'intial_pos' will be the polarization taken for background data
try:
    motor = apt.devices.tdc001.TDC001(serial_port=inputs.motor_port)
    atexit.register(motor.close())
except:
    raise Exception("an error occured while trying to connect to the motor")
else:
    time.sleep(30.0)

# check for the motor connected status, if it starts off as True just continue code, or move and re-home and double check
if not utility.is_mtr_connected(motor):
    print("estabishing connection with motor, one moment please")
    # move 5 degrees, sleep, and then move back
    motor.move_absolute(utility.from_d(5.0))
    time.sleep(5.0)
    motor.move_absolute(utility.from_d(0.0))
    time.sleep(5.0)
# now double check motor connection, if true yay keep going, else send it back to adam for fixin
if not utility.is_mtr_connected(motor):
    raise Exception("motor connection not established, debugging required")
print("motor connection established!")

print("time to collect background!")
motor.register_error_callback(utility.error_callback)

# now move to motor to initial angle and generate background
# once background is generated, create array so the rest of the data can be easily stored
motor.move_absolute(pol_pos_cts[0])
time.sleep(3)
# connect to spectrograph and set integration time
try:
    spectrum = spectro.ocean(inputs.specSN)
    atexit.register(spectrum.close())
except:
    raise Exception("cannot make connection to spectrograph, program ending")
# this is just what the original dscan does, not sure why tho
try:
    spectrum.setinttime(inputs.spec_int_time)
except:
    print("except")
    spectrum.setinttime(inputs.spec_int_time)
time.sleep(2.0)

input("press enter to capture background")
# spectrum.getspec() - 2xN list, float - 1st row is N wavelengths [nm], 2nd is intensity [counts]
background = spectrum.getspec()

f.write("Wavelengths (nm)\n")
wavelengths = background[0]
np.savetxt(f, wavelengths)
f.write("Background (counts)\n")
np.savetxt(f, background[1])

# now to collect the rest of the data
input("Press enter to begin collecting data...")
for i in range(len(pol_pos_cts)):
    # check connection every time
    mtr_connection = utility.is_mtr_connected(motor)
    if mtr_connection:
        motor.move_absolute(pol_pos_cts[i])
        print("moving to", pol_pos_d[i], "deg")
        time.sleep(5.0)
        # check that polarizer angle isn't drifting
        drift = not np.isclose(
            pol_pos_d[i], utility.to_d(motor.status["position"]), atol=0.2
        )
        if drift:
            raise Exception(
                "polarizer has drifted from desired values, ending collection"
            )
    else:
        raise Exception("Polarizer connection lost, ending collection")
    print("collecting")
    spectrometer_output = spectrum.getspec()
    # check that wavelengths havent changed
    if np.allclose(spectrometer_output[0], wavelengths) == False:
        raise Exception(
            "spectrograph is has collected different spectral range, ending collection"
        )
    np.savetxt(f, spectrometer_output[1])


print("Data collection finished")
