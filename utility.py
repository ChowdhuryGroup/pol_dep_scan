import atexit
import time

import numpy as np
import thorlabs_apt_device as apt
from pylablib.devices import Thorlabs as tl

import angles
import oceanOpticSpectrosco as spectro


class AptMotor:
    connection: apt.TDC001

    def __init__(self, port: str) -> None:
        try:
            # We want to establish good connection is present before waiting for homing
            self.connection = apt.devices.tdc001.TDC001(serial_port=port, home=False)
            self.connection.set_enabled(state=True)
        except:
            raise Exception("an error occured while trying to connect to the motor")

        atexit.register(self.connection.close)
        self.connection.set_home_params(
            int(angles.from_dps(10)), int(angles.from_d(3.7))
        )
        time.sleep(1.0)
        print("homing...")

        self.connection.home()
        self.connection.move_absolute(angles.from_d(10.0))
        self.connection.move_absolute(angles.from_d(-10.0))
        for i in range(40):
            time.sleep(1.0)
            print(self.connection.status)

        # Give controller a moment to initialize before asking it if the motor is connected
        time.sleep(1.0)

        # Set acceleration to 10000 counts/s/s, maximum velocity to 2000 counts/s/s
        self.connection.set_velocity_params(10000, 2000)

        if not is_mtr_connected(self.connection):
            print("estabishing connection with motor, one moment please")
            # move 5 degrees, sleep, and then move back
            self.connection.move_absolute(angles.from_d(5.0))
            time.sleep(5.0)
            print(
                "check: ",
                self.connection.status["position"],
                self.connection.status["motor_connected"],
            )
            self.connection.move_absolute(angles.from_d(0.0))
            time.sleep(5.0)
            print("check: ", self.connection.status["position"])

        # now double check motor connection, if true yay keep going, else send it back to adam for fixin
        if not is_mtr_connected(self.connection):
            raise Exception("motor connection not established, debugging required")
        self.connection.register_error_callback(error_callback)
        print("motor connection established!")


class KinesisMotor:
    connection: tl.KinesisMotor

    def __init__(self) -> None:
        print("connecting to back motor, one minute please")
        try:
            bck = tl.KinesisMotor("27263055", scale="stage")
            bck.home()
        except:
            bck.close()
            raise Exception("an error occured while trying to connect to KDC101")
        else:
            time.sleep(60.0)
        # check connection status of back motor
        bck_connection = is_pll_connected(bck)
        if bck_connection:
            print("back motor connection established!")
        else:
            bck.close()
            raise Exception(
                "could not establish connection with back motor, debugging required"
            )


class Spectrograph:
    def __init__(self) -> None:
        print("connecting to spectrograph")
        try:
            spectrum = spectro.ocean(inputs["specSN"])
        except:
            frnt.close()
            bck.close()
            raise Exception("cannot connect to spectrograph, program ending")
        # this is what original dscan does, idk why tho
        try:
            spectrum.setinttime(inputs["spec_int_time"])
        except:
            print("except")
            spectrum.setinttime(inputs["spec_int_time"])
        time.sleep(2.0)


def is_mtr_connected(motor):
    'returns bool value of motor.status["motor_connected"], just input APT device object'
    return motor.status["motor_connected"]


#  pylablib help funct
def is_pll_connected(motor):
    "does get_status to returns bool value of pylablib motor, true if enabled, false otherwise"
    sts = motor.get_status()
    if "enabled" in sts:
        connect = True
    else:
        connect = False
    return connect


# in case the motor throws an error
def error_callback(source, code, note):
    print(f"Device {source} reported error code{code}: {note}")


def list_com_devices():
    "literally what the funct say, just a wrapper for an apt funct"
    print(apt.devices.aptdevice.list_devices())


def pol_step(port, initial, step, final, wait):
    """
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
    """
    # assertions
    assert type(port) == str, "motor_port input must be a str"
    assert isinstance(initial, (float, int)), "intial_pos input must be a float or int"
    assert isinstance(
        final, (float, int)
    ), "final_position input must be a float or int"
    assert isinstance(step, (float, int)), "step input must be float or int"
    assert isinstance(wait, (float, int)), "wait input must be float of int"
    if step < 80.0:
        assert wait > 10.0, "wait gotta be longer champ"
    elif 80.0 < step <= 180.0:
        assert wait > 20.0, "wait gotta be longer champ"
    # connect to the motor
    print("estabishing connection with motor, one minute please")
    try:
        mtr = apt.devices.tdc001.TDC001(serial_port=port)
    except:
        mtr.close()
        raise Exception("an error occured while trying to connect to the motor")
    else:
        time.sleep(60.0)
    # check for the motor connected status, if it starts off as True just continue code, or move and re-home and double check
    mtr_connection = is_mtr_connected(
        mtr
    )  # status if the motor is connected (bool), must always be true
    if mtr_connection == False:
        # move 5 degrees, sleep, and then move back
        mtr.move_relative(angles.from_d(5.0))
        time.sleep(wait)
        mtr.move_absolute(angles.from_d(0.0))
        time.sleep(wait)
    # now double check motor connection, if true yay keep going, else send it back to adam for fixin
    mtr_connection = is_mtr_connected(mtr)
    if mtr_connection:
        print("motor connection established!")
    else:
        mtr.close()
        raise Exception("motor connection not established, debugging required")
    # extra handling from the people that made this
    mtr.register_error_callback(error_callback)
    # desired polarizer positions [deg]
    pol_pos_d = np.arange(initial, final + step, step, dtype=float)
    # desired polarizer pos [cts]
    pol_pos_cts = np.array([angles.from_d(pol_pos_d[i]) for i in range(len(pol_pos_d))])
    # move pol to initial pos, if needed
    if np.isclose(pol_pos_d[0], angles.to_d(mtr.status["position"]), atol=0.2) == False:
        print("moving polarizer to initial position")
        mtr.move_absolute(pol_pos_cts[0])
        time.sleep(wait)
    print("starting polarizer walk")
    # if checks are failed, have a vari that if we had to break the loop it will just end the program after the loop
    did_break = False
    for i in range(len(pol_pos_cts)):
        # check connection every time
        mtr_connection = is_mtr_connected(mtr)
        if mtr_connection:
            mtr.move_absolute(pol_pos_cts[i])
            print("moving to", pol_pos_d[i], "deg")
            time.sleep(wait)
            # check polarizer pos isnt drifting
            drift = np.isclose(
                pol_pos_d[i], angles.to_d(mtr.status["position"]), atol=0.2
            )
            if drift == False:
                print("polarizer has drifted from desired values, ending collection")
                did_break = True
                mtr.close()
                break
        else:
            print("polarizer connection lost, ending collection")
            did_break = True
            mtr.close()
            break
    # handle if had to break loop
    if did_break:
        raise Exception("loop terminated, see message above for why")
    else:
        mtr.close()
        print("loop finished, closing maching connections, bye:)")
