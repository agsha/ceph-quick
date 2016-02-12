import inspect
import json
import logging
import os
import sys
import subprocess
import socket
import xml.etree.ElementTree as ET
from time import sleep

__author__ = 'sharath.g'

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    PRETTY = '\033[1;36m'
    FAIL = '\033[91m'
    TAME = '\033[0;36m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def copy_to_remote(ip):
    call("ssh -o StrictHostKeyChecking=no sharath.g@{ip} 'sudo rm  /tmp/{f}'".format(ip=ip, f=os.path.basename(__file__)))
    call("scp {0} sharath.g@{1}:/tmp".format(os.path.abspath(__file__), ip))


def prettify(cmd, line=-1):
    return "{tame_color}[{host} {cwd}:{line}]$ {bold_color}{cmd}{end_color}".format(tame_color=bcolors.TAME,
                                                                             bold_color=bcolors.PRETTY,
                                                                             host=socket.gethostname(),
                                                                                     cwd=os.getcwd(),
                                                                                     line=line,
                                                                             cmd=cmd, end_color=bcolors.ENDC)


def execute_on_remote(ip, command):
    cc("ssh -o StrictHostKeyChecking=no sharath.g@%s 'sudo python %s %s'" % (
        ip, "/tmp/" + os.path.basename(__file__), command))


def for_each(appId):
    s = co("/home/sharath.g/bin/kloud-cli instance list -e 10.33.65.0 --appId={appId} --json".format(appId=appId))
    s = json.loads(s)
    for obj in s:
        ip = obj['primary_ip']
        host = obj['hostname']
        type = obj['instance_type']
        try:
            copy_to_remote(ip)
            execute_on_remote(ip, "echo")
        except:
            log.debug("failed for {ip}".format(ip=ip))

def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

def lineno2():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_back.f_lineno

def echo(params):
    log.debug("hihihihi")


def cc(cmd):
    log.debug(prettify(cmd, lineno2()))
    subprocess.check_call(cmd, shell=True)


def co(cmd):
    log.debug(prettify(cmd, lineno2()))
    stdout = subprocess.check_output(cmd, shell=True)
    log.debug(stdout)
    return stdout

def call(cmd):
    log.debug(prettify(cmd, lineno2()))
    return subprocess.call(cmd, shell=True)

fsid = ''
cluster_name = ''
host = socket.gethostname()
ip = socket.gethostbyname(socket.gethostname())




def gen(params):
    cluster_name = params[0]
    cc("/bin/bash -x /etc/init.d/ceph stop osd")

    while(True):
        if "/usr/bin/ceph-osd" in co("ps aux | grep ceph-osd"):
            sleep(1)
        else:
            break
    cc("cp /tmp/ceph.client.admin.keyring /tmp/ceph.conf /etc/ceph")

    for l in ['b', 'c', 'd', 'e', 'f', 'g']:
        dev = '/dev/vd'+l
        if not os.path.exists(dev):
            continue

        num = co("ceph osd create").strip()
        cc("echo '[osd.{num}]' >> /etc/ceph/ceph.conf".format(num=num))

        cc("echo '  host={host}' >> /etc/ceph/ceph.conf".format(host=host))
        call("umount {dev}".format(dev=dev))
        cc("sudo mkfs.xfs -f {dev}".format(dev=dev))
        call("mkdir -p /var/lib/ceph/osd/{cluster_name}-{num}".format(cluster_name=cluster_name, num=num))
        cc("sudo mount {dev} /var/lib/ceph/osd/{cluster_name}-{num}".format(dev=dev, cluster_name=cluster_name, num=num))

        cc("sudo ceph-osd -i {num} --mkfs --mkkey ".format(num=num))
        cc("sudo ceph auth add osd.{num} osd 'allow *' mon 'allow profile osd' -i /var/lib/ceph/osd/{cluster_name}-{num}/keyring".format(num=num, cluster_name=cluster_name))
        cc("sudo /etc/init.d/ceph start osd")


def main(params):
    ip = '10.33.57.201'
    copy_to_remote(ip)
    execute_on_remote(ip, "gen ceph" )


# setup logging to console with line number
console = logging.StreamHandler(sys.stdout)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger('').addHandler(console)
logging.getLogger('').setLevel(logging.DEBUG)
log = logging.getLogger(__name__)

if __name__ == '__main__':

    method = 'main'
    if len(sys.argv) > 1:
        method = sys.argv[1]
        params = []
        if len(sys.argv) > 2:
            params = sys.argv[2:]
        globals()[sys.argv[1]](params)
    else:
        main(sys.argv[1:])
