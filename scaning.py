import re
import socket
import fcntl
import struct
import subprocess
from tqdm import tqdm
import datetime
import pexpect


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

        child = pexpect.spawn(f'sudo nmap -sP {ip}/{netmask}')

        full_output = ""
        pbar = tqdm(total=100, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}', colour='green')
        while child.isalive():
            try:
                index = child.expect(['\n', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
                if index == 0:
                    line = child.before.decode()
                    full_output += line + "\n"
                    child.sendline('')
                    percent_done = re.search(r'About (\d+\.\d+)% done', line)
                    if percent_done:
                        pbar.update(float(percent_done.group(1)) - pbar.n)

            except pexpect.exceptions.TIMEOUT:
                continue
        pbar.close()
        remaining_output = child.readlines()
        full_output += "".join([line.decode() for line in remaining_output])

        data = {}
        ip_address = None
        for line in full_output.split('\n'):
            ip_match = re.search(r'Nmap scan report for ([\d\.]+)', line)
            mac_match = re.search(r'MAC Address: ([\w:]+) \((.+)\)', line)

            if ip_match:
                ip_address = ip_match.group(1)
            elif mac_match and ip_address:
                mac_address, mac_name = mac_match.groups()
                data[ip_address] = {'mac_address': mac_address, 'mac_name': mac_name}
                ip_address = None

        return data

    def scan_os(self, active_ips):
        results = {}

        for ip in tqdm(active_ips, bar_format="{l_bar}{bar}", desc="Scanning"):
            now = datetime.datetime.now()
            date_time_string = now.strftime("%Y-%m-%d-%H-%M")
            output_filename = f"os_scan_{ip.replace('.', '_')}_{date_time_string}"
            os_scan = []
            try:
                os_scan = subprocess.check_output(["sudo", "nmap", "-O", "-oA", output_filename, ip],
                                                  stderr=subprocess.DEVNULL).decode()
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

    @staticmethod
    def scan_single(ip):
        scan_output = subprocess.check_output(["sudo", "nmap", "-Pn", "-p-", ip], stderr=subprocess.DEVNULL).decode()
        open_ports = []
        for line in scan_output.split('\n'):
            match = re.search(r'(\d+)/tcp\s+open', line)
            if match:
                open_ports.append(int(match.group(1)))
        service_versions = NetworkScanner.get_ports_version(open_ports, ip)
        return service_versions

    @staticmethod
    def get_ports_version(open_ports, ip):
        now = datetime.datetime.now()
        date_time_string = now.strftime("%Y-%m-%d-%H-%M")
        output_filename = f"ports_version_{ip.replace('.', '_')}_{date_time_string}"

        scan_output = subprocess.check_output(
            ["sudo", "nmap", "-sV", "-p", ",".join(map(str, open_ports)), ip, "-oA", output_filename],
            stderr=subprocess.DEVNULL).decode()

        service_versions = {}
        for line in scan_output.split('\n'):
            match = re.search(r'(\d+)/tcp\s+open\s+(\w+\??)(?:\s+(.*))?', line)
            if match:
                port = int(match.group(1))
                service = match.group(2) if match.group(2) else '-'
                version = match.group(3) if match.group(3) else '-'
                service_versions[port] = {'service': service, 'version': version}
        return service_versions

        # for port, details in service_versions.items():
        #     print(f"Port: {port}")
        #     print(f"Service: {details['service']}")
        #     print(f"Version: {details['version']}")
        #     print("------------------")


def launch_scan():
    scanner = NetworkScanner('wlan0')
    scan_output = scanner.scan_network()
    sorted_ips = sorted(scan_output, key=lambda ip: [int(i) for i in ip.split('.')])
    # print(scan_output)

    return {"active_ips": sorted_ips, "results": scan_output}


if __name__ == "__main__":
    launch_scan()
