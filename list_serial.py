# Class for listing serial ports and selecting serial connections
# Modified by Liam Clink, 2023
# Taken from: https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python

import serial.tools.list_ports


class SerialPorts:
    def __init__(self, ports_list: list):
        self.ports_list = ports_list

    @classmethod
    def get_serial_ports(cls):
        data = []
        ports = list(serial.tools.list_ports.comports())

        for port_ in ports:
            obj = Object(
                data=dict(
                    {
                        "device": port_.device,
                        "description": port_.description.split("(")[0].strip(),
                        # These next two only are present for USB
                        "manufacturer": port_.manufacturer,
                        "serial_number": port_.serial_number,
                    }
                )
            )
            data.append(obj)

        return cls(ports_list=data)

    @staticmethod
    def get_description_by_device(device: str):
        for port_ in SerialPorts.get_serial_ports().ports_list:
            if port_.device == device:
                return port_.description

    @staticmethod
    def get_device_by_description(description: str):
        for port_ in SerialPorts.get_serial_ports().ports_list:
            if port_.description == description:
                return port_.device

    @staticmethod
    def get_device_by_serial_number(serial_number: str):
        for port_ in SerialPorts.get_serial_ports().ports_list:
            if port_.serial_number == serial_number:
                return port_.device


class Object:
    def __init__(self, data: dict):
        self.data = data
        self.device = data.get("device")
        self.description = data.get("description")


if __name__ == "__main__":
    for port in SerialPorts.get_serial_ports().ports_list:
        print(port.device)
        print(port.description)

    print(SerialPorts.get_device_by_description(description="Arduino Leonardo"))
    print(SerialPorts.get_description_by_device(device="COM3"))
