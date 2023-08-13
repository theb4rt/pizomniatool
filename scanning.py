import re
import socket
import fcntl
import struct
import subprocess
from tqdm import tqdm
import datetime
import pexpect


class NetworkScanner:
    def __init__(self, local_ip=None, netmask=None, target_ip=None):
        self.local_ip = local_ip
        self.netmask = netmask
        self.target_ip = None

    def initial_scan(self):
        if self.local_ip and self.netmask:
            active_hosts = self.scan_network(self.local_ip, self.netmask)
            sorted_ips = sorted(active_hosts, key=lambda ip: [int(i) for i in ip.split('.')])
            return {'results': active_hosts, 'active_ips': sorted_ips}

    @staticmethod
    def scan_network(local_ip, netmask):
        now = datetime.datetime.now()
        date_time_string = now.strftime("%Y-%m-%d-%H-%M")
        output_filename = f"active_hosts_{date_time_string}"
        child = pexpect.spawn(f'sudo nmap -sP -oA {output_filename} {local_ip}/{netmask}')
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

    def launch_scan_single(self):
        if self.target_ip is not None:
            return self.scan_single(self.target_ip)

    @staticmethod
    def scan_single(ip):

        child = pexpect.spawn(f'sudo nmap -Pn -p- {ip}')
        full_output = ""
        print("Starting scanning...\n")
        pbar = tqdm(total=100, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}', colour='green')
        last_progress = 0
        while child.isalive():
            try:
                index = child.expect(['\n', pexpect.EOF, pexpect.TIMEOUT], timeout=1)
                if index == 0:
                    line = child.before.decode()
                    full_output += line + "\n"
                    child.sendline('')
                    percent_done = re.search(r'About (\d+\.\d+)% done', line)

                    if percent_done:
                        progress = float(percent_done.group(1))
                        pbar.update(progress - last_progress)
                        last_progress = progress
            except pexpect.exceptions.TIMEOUT:
                continue
        pbar.n = 100
        pbar.refresh()
        print("Complete!\n")

        remaining_output = child.readlines()
        full_output += "".join([line.decode() for line in remaining_output])
        open_ports = []

        for line in full_output.split('\n'):
            match = re.search(r'(\d+)/tcp\s+open', line)
            if match:
                open_ports.append(int(match.group(1)))
        print("open ports: ", ",".join(map(str, open_ports)))
        print("Getting info about ports.\n")

        service_versions = NetworkScanner.get_ports_version(open_ports, ip, pbar)
        return service_versions

    @staticmethod
    def get_ports_version(open_ports, ip, pbar):

        now = datetime.datetime.now()
        date_time_string = now.strftime("%Y-%m-%d-%H-%M")
        output_filename = f"target_{ip.replace('.', '_')}_{date_time_string}.xml"
        child = pexpect.spawn(f'sudo nmap -sV -p {",".join(map(str, open_ports))} {ip} -oA  {output_filename}')
        full_output = ""
        pbar.reset()
        last_progress = 0
        while child.isalive():
            try:
                index = child.expect(['\n', pexpect.EOF, pexpect.TIMEOUT], timeout=1)
                if index == 0:
                    line = child.before.decode()
                    full_output += line + "\n"
                    child.sendline('')
                    percent_done = re.search(r'About (\d+\.\d+)% done', line)

                    if percent_done:
                        progress = float(percent_done.group(1))
                        pbar.update(progress - last_progress)
                        last_progress = progress
            except pexpect.exceptions.TIMEOUT:
                continue
        pbar.close()
        print("Complete!")
        remaining_output = child.readlines()
        full_output += "".join([line.decode() for line in remaining_output])
        service_versions = {}
        for line in full_output.split('\n'):
            match = re.search(r'(\d+)/tcp\s+open\s+(\w+\??)(?:\s+(.*))?', line)
            if match:
                port = int(match.group(1))
                service = match.group(2) if match.group(2) else '-'
                version = match.group(3) if match.group(3) else '-'
                service_versions[port] = {'service': service, 'version': version}
        return service_versions


if __name__ == "__main__":
    scanning = NetworkScanner()
    scanning.target_ip = "192.168.1.100"
    result = scanning.launch_scan_single()
    print(result)
