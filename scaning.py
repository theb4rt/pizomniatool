import re
import socket
import fcntl
import struct
import subprocess
from tqdm import tqdm


class NetworkScanner:
    def __init__(self, ifname):
        self.ifname = ifname

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', self.ifname[:15].encode('utf-8'))
        )[20:24])

    def get_netmask(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        netmask = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x891b,
            struct.pack('256s', self.ifname[:15].encode('utf-8'))
        )[20:24])

        return sum(bin(int(x)).count('1') for x in netmask.split('.'))

    def scan_network(self):
        ip = self.get_ip_address()
        netmask = self.get_netmask()

        scan_hosts_sudo = subprocess.check_output(f"sudo nmap -sP {ip}/{netmask}", shell=True).decode()
        scan_hosts = subprocess.check_output(f"nmap -sP {ip}/{netmask}", shell=True).decode()

        scan_hosts += scan_hosts_sudo

        active_ips = list(set(re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", scan_hosts)))
        if ip in active_ips:
            active_ips.remove(ip)

        return active_ips

    def scan_os(self, active_ips):
        results = {}

        for ip in tqdm(active_ips, bar_format="{l_bar}{bar}", desc="Scanning"):
            os_scan = []
            try:
                os_scan = subprocess.check_output(["sudo", "nmap", "-O", ip], stderr=subprocess.DEVNULL).decode()
            except subprocess.CalledProcessError as e:
                print("Error:", e)

            os_type = re.search(r"OS details: (.+?)\n", os_scan)
            mac_addr = re.search(r"MAC Address: ([\dA-Fa-f:.]+) \((.+?)\)", os_scan)
            try:
                if os_type:
                    results[ip] = {"os_type": os_type.group(1).strip()}
                else:
                    results[ip] = {"os_type": "-"}
                if mac_addr:
                    results[ip]["mac_addr"] = mac_addr.group(1)
                    results[ip]["mac_name"] = mac_addr.group(2)
                else:
                    results[ip]["mac_addr"] = "-"
                    results[ip]["mac_name"] = ""
            except Exception as e:
                results[ip] = {"os_type": "Error"}
                results[ip]["mac_addr"] = "Error"
                results[ip]["mac_name"] = ""
        return results


def launch_scan():
    scanner = NetworkScanner('wlan0')
    active_ips = scanner.scan_network()
    sorted_ips = sorted(active_ips, key=lambda ip: [int(i) for i in ip.split('.')])
    results = scanner.scan_os(sorted_ips)

    return results


if __name__ == "__main__":
    launch_scan()
