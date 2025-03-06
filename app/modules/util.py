from flask import request
from geoip import open_database
import hashlib
import ipaddress
import os
import re
import secrets
import string
import sys

from app.config import Configuration


def determine_location(ip_address: str | ipaddress.IPv4Address) -> str:
    if not isinstance(ip_address, str) and not isinstance(ip_address, ipaddress.IPv4Address):
        raise TypeError(f"Argument 'ip_address' must be of type str or ip_address, not {type(ip_address)}")

    if not ip_address:
        raise ValueError("Argument 'ip_address' must be a non-empty string")

    if isinstance(ip_address, ipaddress.IPv4Address):
        ip_address = str(ip_address)  # GeoIP only works with strings.

    ret: str = None
    geoip_db_path = os.path.join(Configuration.APP_ROOT, "db", "GeoLite2-Country.mmdb")
    with open_database(geoip_db_path) as db:
        match = db.lookup(ip_address)
        if match:
            ret = match.country
    return ret


def determine_mac_address(ip_address: str) -> str:
    """
    Get MAC address for a given IP address by looking it up in the host's ARP table

    :param ip: IP address to look up
    :type ip: str
    :return: MAC address
    :rtype: str
    """

    ret: str = None
    arp_table = get_arp_table()
    if ip_address in arp_table:
        ret = arp_table[ip_address]
    return ret


def get_current_ip_address() -> ipaddress.IPv4Address:
    if request.environ.get("HTTP_X_FORWARDED_FOR") is None:
        ip_address = request.environ["REMOTE_ADDR"]
    else:
        ip_address = request.remote_addr
    return ipaddress.ip_address(ip_address)


def get_arp_table_darwin() -> dict[str, str]:
    """
    Parse the host's ARP table on a macOS machine.

    :return: Machine readable ARP table (by running the "arp -a -n" command)
    :rtype: dict {'ip_address': 'mac_address'}
    """

    ret: dict[str, str] = {}
    devices = os.popen("arp -an")
    for device in devices:
        # Example output: xxxx (192.168.1.254) at xx:xx:xx:xx:xx:xx [ether] on wlp
        _, ip_address, _, phyical_address, _ = device.split(maxsplit=4)
        # Remove the paranthesis around the IP address.
        ip_address = ip_address.strip("()")
        ret[ip_address] = phyical_address
    return ret


def get_arp_table_linux() -> dict[str, str]:
    """
    Parse the host's ARP table on a Linux machine.

    :return: Machine readable ARP table (see the Linux Kernel documentation on /proc/net/arp for more information)
    :rtype: dict {'ip_address': 'mac_address'}
    """

    with open("/proc/net/arp") as proc_net_arp:
        arp_data_raw = proc_net_arp.read(-1).split("\n")[1:-1]

    parsed_arp_table = (dict(zip(("ip_address", "type", "flags", "hw_address", "mask", "device"), v))
                        for v in (re.split("\s+", i) for i in arp_data_raw))

    return {d["ip_address"]: d["hw_address"] for d in parsed_arp_table}


def get_arp_table() -> dict[str, str]:
    """
    Parse the host's ARP table.

    :return: Machine readable ARP table (see the Linux Kernel documentation on /proc/net/arp for more information)
    :rtype: dict {'ip_address': 'mac_address'}
    """

    ret: dict[str, str] = {}
    if sys.platform in ("linux", "linux2"):
        ret = get_arp_table_linux()
    elif sys.platform == "darwin":
        ret = get_arp_table_darwin()
    return ret


def generate_random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def generate_salt() -> str:
    """
    Generates a 64-character salt to use with a hashed password.
    """

    rand = os.urandom(16)
    return hashlib.sha256(rand).hexdigest()
