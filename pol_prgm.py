# motorized polarizer programs to be used with Thorlabs TDC001+PRM1-Z8
# see readme and other .py file for better documentation
# boilerplate
from mimetypes import init # not sure wtf this is
import numpy as np
from functools import partial
import thorlabs_apt_device as apt
import time

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

def list_com_devices():
	'litterally what the funct say, just a wrapper for an apt funct'
	print(apt.devices.aptdevice.list_devices())

def pol_step(port,initial,step,final,wait):
	'''
	connects to motor, moves to initial position, takes however many steps it takes to reach the final position waiting every time
	NOTE: when motor is initialized there is a 50-50 chance it will home to 0 (the marker on the thing) assume it does
	NOTE: pretty sure the motor can only handle 0,360 so this program will only handle that too
	inputs:
	port - str - motor port location, shoul be a COM port
	initial - float - initial pol position [deg]
	step - float - step size the pol will take [deg]
	final - float - final pol position [deg]
	wait - float - time [sec] waited before the pol moves again
	NOTE: if 0.<step<80. then wait > 10 sec, if 80<step<=180 then wait > 20sec
	NO OUTPUTS
	'''
	# assertions
	assert(type(port)==str), 'motor_port input must be a str'
	assert(isinstance(initial,(float,int))), 'intial_pos input must be a float or int'
	assert(isinstance(final,(float,int))), 'final_position input must be a float or int'
	assert(isinstance(step,(float,int))), 'step input must be float or int'
	assert(isinstance(wait,(float,int))), 'wait input must be float of int'
	if (step<80.):
		assert(wait > 10.), 'wait gotta be longer champ'
	elif (80.<step<=180.):
		assert(wait>20.), 'wait gotta be longer champ'
	# connect to the motor
	print('estabishing connection with motor, one minute please')
	try:
		mtr = apt.devices.tdc001.TDC001(serial_port=port)
	except:
		mtr.close()
		raise Exception('an error occured while trying to connect to the motor')
	else:
		time.sleep(60.)
	# check for the motor connected status, if it starts off as True just continue code, or move and re-home and double check
	mtr_connection = is_mtr_connected(mtr) # status if the motor is connected (bool), must always be true
	if (mtr_connection==False):
		# move 5 degrees, sleep, and then move back
		mtr.move_relative(from_d(5.))
		time.sleep(wait)
		mtr.move_absolute(from_d(0.))
		time.sleep(wait)
	# now double check motor connection, if true yay keep going, else send it back to adam for fixin
	mtr_connection = is_mtr_connected(mtr)
	if (mtr_connection):
		print('motor connection established!')
	else:
		mtr.close()
		raise Exception('motor connection not established, debugging required')
	# extra handling from the people that made this
	mtr.register_error_callback(error_callback)
	# desired polarizer positions [deg]
	pol_pos_d = np.arange(initial,final+step,step,dtype=float)
	# desired polarizer pos [cts]
	pol_pos_cts = np.array([from_d(pol_pos_d[i]) for i in range(len(pol_pos_d))])
	# move pol to initial pos, if needed
	if (np.isclose(pol_pos_d[0],to_d(mtr.status['position']),atol=.2)==False):
		print('moving polarizer to initial position')
		mtr.move_absolute(pol_pos_cts[0])
		time.sleep(wait)
	print('starting polarizer walk')
	# if checks are failed, have a vari that if we had to break the loop it will just end the program after the loop
	did_break = False
	for i in range(len(pol_pos_cts)):
		# check connection every time
		mtr_connection = is_mtr_connected(mtr)
		if (mtr_connection):
			mtr.move_absolute(pol_pos_cts[i])
			print('moving to',pol_pos_d[i],'deg')
			time.sleep(wait)
			# check polarizer pos isnt drifting
			drift = np.isclose(pol_pos_d[i],to_d(mtr.status['position']),atol=0.2)
			if (drift==False):
				print('polarizer has drifted from desired values, ending collection')
				did_break = True
				mtr.close()
				break 
		else:
			print('polarizer connection lost, ending collection')
			did_break = True
			mtr.close()
			break
	# handle if had to break loop
	if did_break:
		raise Exception('loop terminated, see message above for why')
	else:
		mtr.close()
		print('loop finished, closing maching connections, bye:)')