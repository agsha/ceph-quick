import inspect
import json
import logging
import os
import sys
import subprocess
import socket
import xml.etree.ElementTree as ET

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
    cc("sudo /etc/init.d/ceph stop")
    cc("sudo rm -rf /var/lib/ceph/mon/{cluster_name}-{host}".format(host=host, cluster_name = cluster_name))
    fsid = co("sudo cat /tmp/fsid").strip()
    cc("ceph-authtool --create-keyring /tmp/ceph.mon.keyring --gen-key -n mon. --cap mon 'allow *'")
    cc("ceph-authtool /tmp/ceph.mon.keyring --import-keyring /tmp/ceph.client.admin.keyring")
    cc("monmaptool --create --clobber --add {host} {ip} --fsid {fsid} /tmp/monmap".format(host=host, ip=ip, fsid=fsid))
    cc("sudo mkdir -p /var/lib/ceph/mon/{cluster_name}-{host}".format(host=host, cluster_name = cluster_name))
    cc("ceph-mon --mkfs --fsid={fsid} -i {host} --monmap /tmp/monmap --keyring /tmp/ceph.mon.keyring".format(host=host, fsid=fsid))
    cc("cp /tmp/ceph.mon.keyring /tmp/ceph.client.admin.keyring /tmp/ceph.conf /etc/ceph")
    cc("sudo /etc/init.d/ceph start mon.{host}".format(host=host))

def main(params):
    ip = '10.33.29.199'
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
