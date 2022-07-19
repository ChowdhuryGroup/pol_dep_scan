# moving motorized thorlabs waveplate while also collecting spectra
# just need to run this file, no program calls nessecary
# for polarization dep SHG measurements
# by Adam Fisher
# import packages, double check you have all of these installed
import numpy as np
from functools import partial
import thorlabs_apt_device as apt
import time
import oceanOpticSpectrosco as spectro 
# NOTE: ^ is just a .py file, you will need it in the same directory as this file
# NOTE: to run the above scripts you also need seabreeze package and pyserial
# NOTE: to install thorlabs_apt_device and seabreeze see line below
# pip install --upgrade thorlabs_apt_device
# conda install -c conda-forge seabreeze

# currently this only works for TDC001 connected to a PRM1Z8 any other devices will have to be added in future

# build conversions for encoder cts (what APT/motor knows) to real units
# TDC001 + PRM1-Z8 factor (f) and time step (t)
t = 2048/(6e6) # sampling time 
f = 1919.6418578623391 # encoder counts per degree factor [cts/deg], different for every stage
a = 65536. # extra factor to when converting velocity and acceleration

# need functs to/from cts to angle [deg], ang velo [deg/s], ang accel [deg/s^2]
# all factors should just be the numbers and program will handle how the factors are supposed to be
def from_ang(angle,factor):
	'funct takes in angle [deg] (float) and converts to angle [cts] (int) that the APT program recognizes'
	return int(factor*angle)
def from_angvel(vel,factor,T):
	'funct takes in anglular velocity [deg/s] (float) and converts to angular velocity [cts/s] (int) that the program recognizes'
	return int(f*T*a*vel)
def from_angacc(acc,factor,T):
	'funct takes in angular acceleration [deg/s^2] (float) and converts to angular acceleration [cts/s^2] (int) that the program recognizes'
	return int(f*T*T*a*acc)
def to_ang(cts,factor):
	'funct takes in angle [cts] (int) from the APT program and converts it to an angle [deg] (float)'
	return (cts/factor)
def to_angvel(cts,factor,T):
	'funct takes in angular velocity [cts/s] (int) from the APT program and converts it to an angular velocity [deg/s] (float)'
	return (cts/(factor*T*a))
def to_angacc(cts,factor,T):
	'funct takes in angular acceleration [cts/s^2] (int) from the APT program and converts it to an angular acceleration [deg/s^2] (float)'
	return (cts/(factor*T*T*a))

# now have partial functs to finish conversion
from_d = partial(from_ang,factor=f)
from_d.__doc__ = 'partial funct takes in angle [deg] and converts to angle [cts]'
from_dps = partial(from_angvel,factor=f,T=t)
from_dps.__doc__ = 'partial funct takes in angle velocity [deg/s] and converts to angle velocity [cts/s]'
from_dpss = partial(from_angacc,factor=f,T=t)
from_dpss.__doc__ = 'partial funct takes in angle acceleration [deg/s^2] and converts to angle acceleration [cts/s^2]'
to_d = partial(to_ang,factor=f)
to_d.__doc__ = 'partial funct takes in angle [cts] and converts to angle [deg]'
to_dps = partial(to_angvel,factor=f,T=t)
to_dps.__doc__ = 'partial funct takes in angle velocity [cts/s] and converts to angle velocity [deg/s]'
to_dpss = partial(to_angacc,factor=f,T=t)
to_dpss.__doc__ = 'partial funct takes in angle acceleration [cts/s^2] and converts to angle acceleration [deg/s^2]'

# other helper functions
def is_mtr_connected(motor):
	'returns bool value of motor.status["motor_connected"], just input APT device object'
	return motor.status['motor_connected']

# in case the motor throws an error
def error_callback(source,msgid,code,notes):
	print(f"Device {source} reported error code{code}: {note}")

# NOTE: MUST use some sort of iteration method if you wish to use conversion functions with numpy arrays
# NOTE: this script will connect to controller will intialize and exit once it is over to prevent bad errors
# NOTE: serial number for TDC001 should be '83------'. however, adam's wasnt but stil worked, just watch out
# NOTE: need 0 <= intial and final position of polarizer <=360 [deg]
# NOTE: this assumes that the spectrograph's .getspec() program gets the same number of wavelengths each time
# NOTE: encoding utf-8
# NOTE: will not allow overwriting for files, if you dont change the name it was throw an error and youll have to take the data again

# print dict of important values so that they can be double checked
# list devices so you can find the controller
# things not included: motor pid/vid/serial#, any other spectrograph inputs

# replace the word input with the required information
inputs = {
	'motor_port': 'input' # motor port location (str)
	'intial_pos': 'input' # waveplates inital position [deg] (float), background data taken at this position
	'final_position': 'input' # waveplates final position [deg] (float)
	'step': 'input' # angular distance traveled between each spectrograph measurement [deg] (float)
	'specSN': 'input' # spectrograph serial # (str)
	'spec_int_time': 'input' # spectrograph integration time [msec] (int?)
	'fname': 'input' # file name that data will saved under (str), MUST BE A .txt file
	'path': 'input' # relative path to directory you would like the file saved to (str)
}
print('Here is a list of devices that may help')
print(apt.devices.aptdevice.list_devices())
print('Checking the inputs dict that the nessecary inputs are correct to run this program')
print('If any entries are still are still just str(input) its gonna throw an error')
for i in inputs:
	if (inputs[i]=='input'):
		raise Exception('nice try mf, input values need to be entered already')
# do assertion errors for inputs
assert(type(inputs['motor_port'])==str), 'motor_port input must be a str'
assert(isinstance(inputs['intial_pos'],(float,int))), 'intial_pos input must be a float or int'
assert(isinstance(inputs['final_position'],(float,int))), 'final_position input must be a float or int'
assert(isinstance(inputs['step'],(float,int))), 'step input must be float or int'
assert(isinstance(inputs['specSN'],str)), 'specSN input must be str'
assert(isinstance(inputs['spec_int_time'],(float,int))), 'spec_int_time input must be float or int'
assert(isinstance(inputs['fname'],str)), 'fname input must be str'
assert(isinstance(inputs['path'],str)), 'path input must be str'

# now connect to the machines
# connect to motor first as 'intial_pos' will be the polarization taken for background data
try:
	mtr = apt.devices.tdc001.TDC001(serial_port=inputs['motor_port'])
except:
	mtr.close()
	raise Exception('an error occured while trying to connect to the motor')
else:
	time.sleep(30.)
# check for the motor connected status, if it starts off as True just continue code, or move and re-home and double check
mtr_connection = is_mtr_connected(mtr) # status if the motor is connected (bool), must always be true
if (mtr_connection==False):
	print('estabishing connection with motor, one moment please')
	# move 5 degrees, sleep, and then move back
	mtr.move_absolute(from_d(5.))
	time.sleep(5.)
	mtr.move_absolute(from_d(0.))
	time.sleep(5.)
# now double check motor connection, if true yay keep going, else send it back to adam for fixin
mtr_connection = is_mtr_connected(mtr)
if (mtr_connection):
	print('motor connection established!')
else:
	mtr.close()
	raise Exception('motor connection not established, debugging required')
print('time to collect background!')
mtr.register_error_callback(error_callback)
# now move to motor to initial position and generate background
# once background is generated, create array so the rest of the data can be easily stored
# NEED TO FIX POL POS D
pol_pos_d = np.arange(inputs['intial_pos'],(inputs['final_position']+inputs['step']),inputs['step'],dtype=float) # desired polarizer positions [deg]
pol_pos_cts = np.array([pol_pos_d[i] for i in range(len(pol_pos_d))]) # desired polarizer pos [cts]
# move polarizer to first position 
mtr.move_absolute(pol_pos_cts[0])
time.sleep(3)
# connect to spectrograph and set integration time
try:
	spectrum = spectro.ocean(inputs['specSN'])
except:
	mtr.close()
	raise Exception('cannot make connection to spectrograph, program ending')
# this is just what the original dscan does, not sure why tho
try:
	spectrum.setinttime(inputs['spec_int_time'])
except:
	print('except')
	spectrum.setinttime(inputs['spec_int_time'])
time.sleep(2.)
input('press enter to capture background')
bkg = spectrum.getspec() # background
# spectrum.getspec() - 2xN list?, float - 1st row is N wavelengths [nm?], 2nd is intensity [counts]
# create array to save all data, assuming spectrograph collects the same wavelength every time spectrum.getspec() is ran
# format: Nx(M+2) array, [[wvl],[bkg],[I(1st pol pos)],...,[I(ith pol pos)],...,[I(Nth pol pos)]]
# where wvl,bkg,I(pos) Nx1 col arrays
data = np.zeros((len(bkg[0]),(len(pol_pos_d)+2)),dtype=float)
# now place the background and wvl in the first two columns
data[:,0] = bkg[0]
data[:,1] = bkg[1]
# now to collect the rest of the data
input('press enter to begin collecting data')
# if checks are failed, have a vari that if we had to break the loop it will just end the program after the loop
did_break = False
for i in range(len(pol_pos_cts)):
	# check connection every time
	mtr_connection = is_mtr_connected(mtr)
	if (mtr_connection):
		mtr.move_absolute(pol_pos_cts[i])
		print('moving to',pol_pos_d[i],'deg')
		time.sleep(5.)
		# check polarizer pos isnt drifting
		drift = np.isclose(pol_pos_d[i],to_d(mtr.status['position']),atol=0.2)
		if (drift==False):
			print('polarizer has drifted from desired values, ending collection')
			did_break = True
			mtr.close()
			spectrum.close()
			break 
	else:
		print('polarizer connection lost, ending collection')
		did_break = True
		mtr.close()
		spectrum.close()
		break
	print('collecting')
	x = spectrum.getspec()
	# check that wavelengths havent changed
	if (np.allclose(x[0],data[:,0])==False):
		print('spectrograph is has collected different spectral range, ending collection')
		did_break = True
		mtr.close()
		spectrum.close()
		break
	# put the new data into the array
	data[:,(2+i)] = x[1]
# check if loop had to break 
if (did_break):
	print('an error occured during the collection, nothing has been saved')
	raise Exception('see above for specific issue, ending program')
else:
	print('collection finished, saving data, closing machine connections')
	mtr.close()
	spectrum.close()
# using np.savetxt, so estabilish headers and such
cmt = 'file was created at:' + time.asctime()+'\n' + 'polarizer positions [deg]:\n' + str(pol_pos_d)
# open file, will not overwrite!
try:
	with open(inputs['path']+inputs['fname'],'x',encoding='utf-8') as f:
		np.savetxt(inputs['path']+inputs['fname'],data,delimiter=',',header=cmt,encoding='utf=8')
except FileExistsError:
	print('this file name already exisits, i wont let you overwrite your data!')
	new_fname = input('please put a new (unused) file name here:')
	with open(inputs['path']+new_fname,'x',encoding='utf-8') as f:
		np.savetxt(inputs['path']+new_fname,data,delimiter=',',header=cmt,encoding='utf-8')
print('saving completed, have a nice day :)')