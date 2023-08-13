import fcntl
import socket
import struct
import psutil


class NetworkInfo:
    def __init__(self, interface='wlan0', ip=None, mask=None, mac=None):
        self.interface = interface
        self.ip = ip
        self.mask = mask
        self.mac = mac

    @property
    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,
                struct.pack('256s', self.interface[:15].encode('utf-8'))
            )[20:24])
            s.close()
            return ip
        except Exception as e:
            return None

    @property
    def get_netmask(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            netmask = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x891b,
                struct.pack('256s', self.interface[:15].encode('utf-8'))
            )[20:24])
            s.close()
            return sum(bin(int(x)).count('1') for x in netmask.split('.'))
        except Exception as e:
            return None

    @staticmethod
    def get_available_interfaces():
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            if interface == 'lo':
                continue
            interfaces.append(interface)

        return interfaces


if __name__ == '__main__':
    network_info_eth0 = NetworkInfo(interface='eno1')
