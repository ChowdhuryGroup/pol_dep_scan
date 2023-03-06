from functools import partial

# NOTE: MUST use some sort of iteration method if you wish to use conversion functions with numpy arrays


# build conversions for encoder cts (what APT/motor knows) to real units
# PRM1-Z8 factor (f) and time step (t) (found in APT Communications Protocol: https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf)
t = 2048 / (6e6)  # sampling time
f = 1919.6418578623391  # encoder counts per degree factor [cts/deg], different for every stage
a = 65536.0  # extra factor to when converting velocity and acceleration

# need functs to/from cts to angle [deg], ang velo [deg/s], ang accel [deg/s^2]
# all factors should just be the numbers and program will handle how the factors are supposed to be
def from_ang(angle, factor):
    "funct takes in angle [deg] (float) and converts to angle [cts] (int) that the APT program recognizes"
    return int(factor * angle)


def from_angvel(vel, factor, T):
    "funct takes in anglular velocity [deg/s] (float) and converts to angular velocity [cts/s] (int) that the program recognizes"
    return int(f * T * a * vel)


def from_angacc(acc, factor, T):
    "funct takes in angular acceleration [deg/s^2] (float) and converts to angular acceleration [cts/s^2] (int) that the program recognizes"
    return int(f * T * T * a * acc)


def to_ang(cts, factor):
    "funct takes in angle [cts] (int) from the APT program and converts it to an angle [deg] (float)"
    return cts / factor


def to_angvel(cts, factor, T):
    "funct takes in angular velocity [cts/s] (int) from the APT program and converts it to an angular velocity [deg/s] (float)"
    return cts / (factor * T * a)


def to_angacc(cts, factor, T):
    "funct takes in angular acceleration [cts/s^2] (int) from the APT program and converts it to an angular acceleration [deg/s^2] (float)"
    return cts / (factor * T * T * a)


# now have partial functs to finish conversion
from_d = partial(from_ang, factor=f)
from_d.__doc__ = "partial funct takes in angle [deg] and converts to angle [cts]"
from_dps = partial(from_angvel, factor=f, T=t)
from_dps.__doc__ = "partial funct takes in angle velocity [deg/s] and converts to angle velocity [cts/s]"
from_dpss = partial(from_angacc, factor=f, T=t)
from_dpss.__doc__ = "partial funct takes in angle acceleration [deg/s^2] and converts to angle acceleration [cts/s^2]"
to_d = partial(to_ang, factor=f)
to_d.__doc__ = "partial funct takes in angle [cts] and converts to angle [deg]"
to_dps = partial(to_angvel, factor=f, T=t)
to_dps.__doc__ = "partial funct takes in angle velocity [cts/s] and converts to angle velocity [deg/s]"
to_dpss = partial(to_angacc, factor=f, T=t)
to_dpss.__doc__ = "partial funct takes in angle acceleration [cts/s^2] and converts to angle acceleration [deg/s^2]"
