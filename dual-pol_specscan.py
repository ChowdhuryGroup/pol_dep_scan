# program to automate synchonized movement of two motorized waveplates (Thorlabs PRM1Z8, Newport URS50) and spectroscopic data collection (Ocean Optics SpectraPro HRS-300)
# this is done by interfacing with the waveplates' controller (Thorlabs TDC001, Newport CONEX-CC hard wired to wvplt)
# for polarization dependant spectroscopic measurements (SHG)

# By Adam Fisher
# further documentation is in README

# double check you have these packages
import numpy as np
from functools import partial
import thorlabs_apt_device as apt
from pylablib.devices import Thorlabs as tl
import time
import oceanOpticSpectrosco as spectro
# NOTE: ^ is just a .py file, you will need it in the same directory as this file
# NOTE: to run the above scripts you also need seabreeze package and pyserial
# NOTE: to install thorlabs_apt_device and seabreeze see line below
# pip install --upgrade thorlabs_apt_device
# conda install -c conda-forge seabreeze
# conda install -c conda-forge pylablib
# ^ double check you have installed all dependancies before using (check documentation)

# apt conversion for TDC001 + PRM1Z8
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

# apt helper functions
def is_apt_connected(motor):
	'returns bool value of motor.status["motor_connected"], just input APT device object'
	return motor.status['motor_connected']

# in case the apt motor throws an error
def error_callback(source,msgid,code,notes):
	print(f"Device {source} reported error code{code}: {note}")

#  pylablib help funct
def is_pll_connected(motor):
	'does get_status to returns bool value of pylablib motor, true if enabled, false otherwise'
	sts = motor.get_status()
	if 'enabled' in sts:
		connect = True
	else:
		connect = False
	return connect


# printing device list and input's dict keys
print('here is some device info for you')
print(apt.devices.aptdevice.list_devices())
print(tl.list_kinesis_devices())

# NOTE: going to decide front/back by com port
# NOTE: need to know which motor is which for connection purposes
# NOTE: keep the pol controlled by the TDC001 in FRONT, switch is not supported currently (1/9/23)
# NOTE: dont actually need port of KDC101, just serial # which is 27263055

# replace the word input with required information
inputs = {
	'front_port': 'input', # front pol port location (str)
	'TDC_front': 'input', # is the pol controlled by the TDC001 the front pol (bool)
	'KDC_SN': 'input', # KDC101 serial number, should be back pol (str)
	'intial_pos': 'input', # front waveplates inital position [deg] (float), background data taken at this position
	'final_position': 'input', #  front waveplates final position [deg] (float)
	'offset': 'input', # orientation of back pol w.r.t front pol [deg] (float)
	'step': 'input', # angular distance traveled between each spectrograph measurement [deg] (float)
	'wait': 'input', # wait time [sec] before pol moves again (float or int)
	'specSN': 'input', # spectrograph serial # (str)
	'spec_int_time': 'input', # spectrograph integration time [msec] (int?)
	'fname': 'input', # file name that data will saved under (str), MUST BE A .txt file
	'path': 'input' # relative path to directory you would like the file saved to (str)
}

print('checking that the input dictionary has been filled out correctly')
for i in inputs:
	if (inputs[i]=='input'):
		raise Exception('nice try mf, input values need to be entered already')
# do assertion errors for inputs
assert(type(inputs['front_port'])==str), 'front_port input must be a str'
assert(inputs['TDC_front']), 'TDC must be in front'
assert(isinstance(inputs['KDC_SN'],str)), 'KDC serial number input must be str'
assert(isinstance(inputs['intial_pos'],(float,int))), 'intial_pos input must be a float or int'
assert(isinstance(inputs['final_position'],(float,int))), 'final_position input must be a float or int'
assert(isinstance(inputs['step'],(float,int))), 'step input must be float or int'
assert(isinstance(inputs['wait'],(float,int))), 'wait input must be float or int'
if (inputs['step']<80.):
	assert(inputs['wait']>=10.), 'wait has gotta be longer champ'
elif (80.<inputs['step']<180.):
	assert(inputs['wait']>=20.), 'wait has gotta be longer champ'
assert(isinstance(inputs['offset'],(float,int))), 'offset input must be float or int'
assert(isinstance(inputs['specSN'],str)), 'specSN input must be str'
assert(isinstance(inputs['spec_int_time'],(float,int))), 'spec_int_time input must be float or int'
assert(isinstance(inputs['fname'],str)), 'fname input must be str'
assert(isinstance(inputs['path'],str)), 'path input must be str'

# now connect to machines
# front pol
print('connecting to front motor, one minute please')
try:
	frnt = apt.devices.tdc001(serial_port=inputs['front_port'])
except:
	frnt.close()
	raise Exception('an error occured while trying to connect to TDC001')
else:
	time.sleep(60.)
# check connection status of front motor
frnt_connection = is_apt_connected(frnt)
if (frnt_connection==False):
	print('checking front motor connection')
	frnt.move_relative(from_d(5.))
	time.sleep(5.)
	frnt.move_absolute(from_d(0.))
	time.sleep(5.)
frnt_connection = is_mtr_connected(frnt)
if (frnt_connection):
	print('front motor connection established!')
else:
	frnt.close()
	raise Exception('could not establish connection to front motor, debugging required')
frnt.register_error_callback(error_callback)


print('connecting to back motor, one minute please')
try:
	bck = tl.KinesisMotor('27263055',scale='stage')
	bck.home()
except:
	bck.close()
	raise Exception('an error occured while trying to connect to KDC101')
else:
	time.sleep(60.)
# check connection status of back motor
bck_connection = is_pll_connected(bck)
if (bck_connection):
	print('back motor connection established!')
else:
	bck.close()
	raise Exception('could not establish connection with back motor, debugging required')

print('connecting to spectrograph')
try:
	spectrum = spectro.ocean(inputs['specSN'])
except:
	frnt.close()
	bck.close()
	raise Exception('cannot connect to spectrograph, program ending')
# this is what original dscan does, idk why tho
try:
	spectrum.setinttime(inputs['spec_int_time'])
except:
	print('except')
	spectrum.setinttime(inputs['spec_int_time'])
time.sleep(2.)

# moving pols to their starting pos and taking background
pol_pos_d = np.arange(inputs['intial_pos'],(inputs['final_position']+inputs['step']),inputs['step'],dtype=float) # desired polarizer positions [deg]
pol_pos_cts = np.array([pol_pos_d[i] for i in range(len(pol_pos_d))]) # desired polarizer pos [cts]
pol_pos_bck = pol_pos_d + inputs['offset']

print('time to collect background')
frnt.move_absolute(pol_pos_cts[0])
bck.move_to(pol_pos_bck[0])
time.sleep(5.)

input('press enter to collect background')
bkg = spectrum.getspec() 
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
	# check connections every time
	frnt_connection = is_apt_connected(frnt)
	bck_connection = is_pll_connected(bck)
	if (frnt_connection and bck_connection):
		print('moving to ', pol_pos_d[i], ' and ',pol_pos_bck[i],' deg')
		frnt.move_absolute(pol_pos_cts[i])
		bck.move_to(pol_pos_bck[i])
		time.sleep(inputs['wait'])
		# check pol drift
		df = np.isclose(pol_pos_d[i],to_d(frnt.status['position']),atol=0.2)
		db = np.isclose(pol_pos_bck[i],bck.get_position(),atol=0.2)
		if (df==False) or (db==False):
			print('a polarizer has drifted from desired values, ending collection')
			did_break = True
			break
	else:
		print('connection a polarizer was lost, ending collection')
		did_break = True
		break
	print('collecting')
	x = spectrum.getspec()
	# check its collecting the same spectrum
	if (np.allclose(x[0],data[:,0])==False):
		print('spectrograph has collected different spectral range, ending collection')
		did_break = True
		break
	# put new data into array
	data[:,(2+i)] = x[1]
# check if loop was exited early
if (did_break):
	print('an error occured during collection, nothing has been saved, closing connections')
	frnt.close()
	bck.close()
	spectrum.close()
	raise Exception('see above for specific issue, ending program')
else:
	print('collection finished, saving data, closing connections')
	frnt.close()
	bck.close()
	spectrum.close()
# using np.savetxt, set up headers
cmt = 'file was created at: ' + time.asctime()+'\n' + 'back polarizer was offset by: ' + str(inputs['offset'])+'\n' + 'front polarizer positions [deg]:\n' + str(pol_pos_d)
# open file, will not overwrite
try:
	with open(inputs['path']+inputs['fname'],'x',encoding='utf-8') as f:
		np.savetxt(f,data,delimiter=',',header=cmt,encoding='utf-8')
except FileExistsError:
	print('this file already exists, i wont let you overwrite your data!')
	new_fname = input('please put unused file name here:')
	if (new_fname.[-4:]!='.txt'):
		new_fname += '.txt'
	with open(inputs['path']+new_fname,'x',encoding='utf-8') as g:
		np.savetxt(g,data,delimiter=',',header=cmt,encoding='utf-8')
print('saving completed, have a nice day :)')