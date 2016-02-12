import inspect
import json
import logging
import os
import sys
import subprocess
import socket
import xml.etree.ElementTree as ET

import re
from jinja2 import Template

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
    dir = '/tmp/fetch'
    os.chdir(dir)
    data = []
    for name in filter(None, co("ls {dir}".format(dir=dir)).split()):
        log.debug(name)
        if not os.path.exists(name):
            continue
        with open(name) as f:
            data.append(json.load(f))
    host_info = {}
    with open('/tmp/host_info.json') as f:
        host_info = json.load(f)


    # generate the config files
    call("mkdir -p /tmp/ceph")
    os.chdir("/tmp/ceph")
    cc("uuidgen > /tmp/ceph/fsid")
    fsid = co("cat /tmp/ceph/fsid")
    cc("ceph-authtool --create-keyring ceph.client.admin.keyring --gen-key -n client.admin --set-uid=0 --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'")
    mon_ips = []
    mon_hosts = []
    mons = []
    for d in data:
        if d['ip'] not in host_info['mons']:
            continue
        mon_ips.append(d['ip'])
        mon_hosts.append(d['hostname'])
        mons.append(d)

    mon_ips = ",".join(mon_ips)
    mon_hosts = ",".join(mon_hosts)
    with open("/tmp/ceph.conf.j2") as f:
        t = Template(f.read())
        with open("ceph.conf", "w") as conf:
            conf.write(t.render(mon_hosts=mon_hosts, mon_ips=mon_ips, fsid = fsid, mons=mons))
    cc("cp ceph.conf ceph.client.admin.keyring /etc/ceph")


# todo(sharath) refactor this
def crush(params):
    host_to_osd_num = {}
    p_host = re.compile(r'host (?P<host>\S+) {')
    p_os_num = re.compile(r'\s+item osd.(?P<osd_num>\d+) weight')
    cur_host = ''
    devices = []
    cc("sudo ceph osd getcrushmap -k /etc/ceph/ceph.client.admin.keyring  -o /tmp/oo")
    cc("crushtool -d /tmp/oo -o /tmp/crush")
    with open("/tmp/crush") as f:
        for line in f:
            m = p_host.match(line)
            if m:
                cur_host = m.group('host')
            m = p_os_num.match(line)
            if m:
                if cur_host not in host_to_osd_num:
                    host_to_osd_num[cur_host] = []
                num = m.group('osd_num')
                host_to_osd_num[cur_host].append(num)
                devices.append("device {num} osd.{num}".format(num=num))
    buckets = []
    # generate hosts
    host_info = {}
    with open('/tmp/host_info.json') as f:
        host_info = json.load(f)
    iaas_info = json.loads(co("curl --silent 'http://10.33.65.0:8080/apps/dev-d42sharath1/instances'"))

    racks = {}
    buckets = []
    devices = []
    type = {"0": "hdd", "1": "ssd"}
    for host in host_info['osds']:
        rack = ''
        for vm in iaas_info:
            if vm['primary_ip'] == host:
                rack = vm['detail']['fault_domain_id']
                break
        if rack not in racks:
            racks[rack] = {
                'rot': host['disks'][0]['rot'],
                'hosts':[host]
            }
        else:
            racks[rack]['hosts'].append(host)
        log.debug(host)
    #     buckets.append("host {host}-{type} {".format(host=host, type=type[str(host['disks'][0]['rot'])]))
    #     buckets.append("  alg straw")
    #     buckets.append("  hash 0")
    #     for osd_num in host_to_osd_num[host]:
    #         buckets.append("  item osd.{osd_num} weight 1.0".format(osd_num=osd_num))
    #     buckets.append("}")
    # dc = {'0':[], '1':[]}
    # for rack in racks:
    #     t = type[str(racks[rack]['rot'])]
    #     buckets.append("rack {rack}-{type} {".format(rack=rack, type=t))
    #     buckets.append("  alg straw")
    #     buckets.append("  hash 0")
    #     for host in racks['hosts']:
    #         buckets.append("  item {host}-{type}".format(host=host, type=t))
    #     buckets.append("}")
    #     dc[t].append(rack)
    #
    # buckets.append("datacenter in-chennai-1-ssd {")
    # buckets.append("  alg straw")
    # buckets.append("  hash 0")
    # for rack in dc['0']:
    #     t = type[str(racks[rack]['rot'])]
    #     buckets.append("  item {rack}-{type}".format(rack=rack, type=t))
    # buckets.append("}")
    #
    # buckets.append("datacenter in-chennai-1-hdd {")
    # buckets.append("  alg straw")
    # buckets.append("  hash 0")
    # for rack in dc['1']:
    #     t = type[str(racks[rack]['rot'])]
    #     buckets.append("  item {rack}-{type}".format(rack=rack, type=t))
    # buckets.append("}")
    # with open("/tmp/crush_map.j2") as f:
    #     t = Template(f.read())
    #     with open("/tmp/crush_map", "w") as c:
    #         c.write(t.render(buckets=buckets, devices=devices))
    #



def main(params):
    ip = '10.33.105.206'
    copy_to_remote(ip)
    execute_on_remote(ip, "gen" )
    execute_on_remote(ip, "crush" )


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
