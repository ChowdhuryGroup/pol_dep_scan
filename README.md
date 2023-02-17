# shg-polarization-scan

Script to run to automate a polarization dependent spectrograph scan
for use in OSU's Chowdhury Lab
by Adam Fisher

Currently there is only support for interfacing with only the Thorlabs TDC001 motorized stage controller
Thorlabs KDC101 controller connected to Thorlabs PRM1Z8 motorized waveplate
connected to a Thorlabs PRM1Z8 rotating polarizer and the Ocean Optics SpectraPro HRS-300 spectrometer

## Third Party Dependencies

requires 4 packages: thorlabs_apt_device, pyserial, pylablib, and seabreeze (links below)
APT: <https://thorlabs-apt-device.readthedocs.io/en/latest/index.html>
Seabreeze: <https://python-seabreeze.readthedocs.io/en/latest/index.html>
pyserial: <https://pyserial.readthedocs.io/en/latest/pyserial.html>
PyLabLib: <https://pylablib.readthedocs.io/en/stable/index.html>
oceanOpticSpectrosco, which is just a python file that needs to be in top level directory
These all have dependencies so read their documentation
both of these packages as well as this one has no relation to their respective companies

To install:
pip install --upgrade thorlabs_apt_device
conda install -c conda-forge seabreeze

currently only supports interfacing with:
Thorlabs TDC001 controller connected to Thorlabs PRM1Z8 motorized waveplate
Thorlabs KDC101 controller connected to Thorlabs PRM1Z8 motorized waveplate
polarizer and the Ocean Optics SpectraPro HRS-300 spectrometer

### Three ways to use

dual-pol_specscan.py - automates both waveplates and spectrometer, saves data
pol_dep_specscan.py - automates ONLY TDC001 controlled waveplate and spectrometer, saves data
pol_prgm.py - automates ONLY TDC001 controlled waveplate Thorlabs waveplate

### Please read the .py script before running

you must adjust the script to have the desired inputs before running (and save as well) for the program to work
once that is done all you need to do is run the script press enter twice and it will take the measurements and save the data on its own

## the program also takes the background in the beginning

but the background measurement is sandwiched between two user inputs (press enter once ready) so that you can ensure you are ready to take the background measurement and then again so that you are ready to take the full measurement

## How is Data Saved

data is saved as a .tsv file, you are required to specify the file name and its destination.

there is a header that has the time the file was created and the array of positions of the polarizer when data was collected [degress]. They have the '#' character in front to be compatible with numpy.loadtxt or numpy.genfromtxt
