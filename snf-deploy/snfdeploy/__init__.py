# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import os
import argparse
import sys
import re
import random
import ast
import glob
from snfdeploy.lib import check_pidfile, create_dir, get_default_route, \
    random_mac, Conf, Env, Status
# from snfdeploy import fabfile
from snfdeploy import fabfile
from fabric.api import hide, settings, execute, show


def print_available_actions(command):

    if command == "keygen":
        print """
Usage: snf-deploy keygen [--force]

  Generate new ssh keys (both rsa and dsa keypairs)

  """

    if command == "vcluster":
        print """
Usage: snf-deploy vcluster

  Run the following actions concerning the local virtual cluster:

    - Download base image and create additional disk \
(if --create-extra-disk is passed)
    - Does all the network related actions (bridge, iptables, NAT)
    - Launches dnsmasq for dhcp server on bridge
    - Creates the virtual cluster (with kvm)

  """

    if command == "backend":
        print """
Usage: snf-deploy backend

  Run the following actions concerning a ganeti backend:

    - Create and add a backend to cyclades

  """

    if command == "run":
        print """
Usage: snf-deploy run <action> [<action>...]

  Run any of the following fabric commands:

    Role setup:

      setup_ns_role
      setup_nfs_role
      setup_db_role
      setup_mq_role
      setup_astakos_role
      setup_pithos_role
      setup_cyclades_role
      setup_cms_role
      setup_ganeti_role
      setup_master_role
      setup_stats_role
      setup_client_role

    Helper commands:

      update_env_with_user_info
      update_env_with_service_info
      update_env_with_backend_info

    Admin commands:

      update_ns_for_node
      update_exports_for_node
      allow_db_access
      add_ganeti_backend
      add_synnefo_user
      activate_user
      set_default_quota
      add_public_networks
      add_image


    Custom command:

      setup --node NODE [--role ROLE | --method METHOD --component COMPONENT]

  """

    sys.exit(1)


def create_dnsmasq_files(args, env):

    print("Customize dnsmasq..")
    out = env.dns

    hostsfile = open(out + "/dhcp-hostsfile", "w")
    optsfile = open(out + "/dhcp-optsfile", "w")
    conffile = open(out + "/conf-file", "w")

    for node, info in env.nodes_info.iteritems():
        # serve ip and hostname to nodes
        hostsfile.write("%s,%s,%s,2m\n" % (info.mac, info.ip, info.hostname))

    hostsfile.write("52:54:56:*:*:*,ignore\n")

    # Netmask
    optsfile.write("1,%s\n" % env.net.netmask)
    # Gateway
    optsfile.write("3,%s\n" % env.gateway)
    # Namesevers
    optsfile.write("6,%s\n" % "8.8.8.8")

    dnsconf = """
user=dnsmasq
bogus-priv
no-poll
no-negcache
leasefile-ro
bind-interfaces
except-interface=lo
dhcp-fqdn
no-resolv
# disable DNS
port=0
""".format(env.ns.ip)

    dnsconf += """
# serve domain and search domain for resolv.conf
domain={5}
interface={0}
dhcp-hostsfile={1}
dhcp-optsfile={2}
dhcp-range={0},{4},static,2m
""".format(env.bridge, hostsfile.name, optsfile.name,
           env.domain, env.net.network, env.domain)

    conffile.write(dnsconf)

    hostsfile.close()
    optsfile.close()
    conffile.close()


def cleanup(args, env):
    print("Cleaning up bridge, NAT, resolv.conf...")

    for f in os.listdir(env.run):
        if re.search(".pid$", f):
            check_pidfile(os.path.join(env.run, f))

    create_dir(env.run, True)
    # create_dir(env.cmd, True)
    cmd = """
    iptables -t nat -D POSTROUTING -s {0} -o {1} -j MASQUERADE
    echo 0 > /proc/sys/net/ipv4/ip_forward
    iptables -D INPUT -i {2} -j ACCEPT
    iptables -D FORWARD -i {2} -j ACCEPT
    iptables -D OUTPUT -o {2} -j ACCEPT
    """.format(env.subnet, get_default_route()[1], env.bridge)
    os.system(cmd)

    cmd = """
    ip link show {0} && ip addr del {1}/{2} dev {0}
    sleep 1
    ip link set {0} down
    sleep 1
    brctl delbr {0}
    """.format(env.bridge, env.gateway, env.net.prefixlen)
    os.system(cmd)


def network(args, env):
    print("Create bridge..Add gateway IP..Activate NAT.."
          "Append NS options to resolv.conf")

    cmd = """
    ! ip link show {0} && brctl addbr {0} && ip link set {0} up
    sleep 1
    ip link set promisc on dev {0}
    ip addr add {1}/{2} dev {0}
    """.format(env.bridge, env.gateway, env.net.prefixlen)
    os.system(cmd)

    cmd = """
    iptables -t nat -A POSTROUTING -s {0} -o {1} -j MASQUERADE
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -I INPUT 1 -i {2} -j ACCEPT
    iptables -I FORWARD 1 -i {2} -j ACCEPT
    iptables -I OUTPUT 1 -o {2} -j ACCEPT
    """.format(env.subnet, get_default_route()[1], env.bridge)
    os.system(cmd)


def image(args, env):
    #FIXME: Create a clean wheezy image and use it for vcluster
    if env.os == "ubuntu":
        url = env.ubuntu_image_url
    else:
        url = env.squeeze_image_url

    disk0 = "{0}/{1}.disk0".format(env.images, env.os)
    disk1 = "{0}/{1}.disk1".format(env.images, env.os)

    if url and not os.path.exists(disk0):
        cmd = "wget {0} -O {1}".format(url, disk0)
        os.system(cmd)

    if ast.literal_eval(env.create_extra_disk) and not os.path.exists(disk1):
        if env.lvg:
            cmd = "lvcreate -L30G -n{0}.disk1 {1}".format(env.os, env.lvg)
            os.system(cmd)
            cmd = "ln -s /dev/{0}/{1}.disk1 {2}".format(env.lvg, env.os, disk1)
            os.system(cmd)
        else:
            cmd = "dd if=/dev/zero of={0} bs=10M count=3000".format(disk1)
            os.system(cmd)


def fabcommand(args, env, actions, nodes=[]):
    levels = ["status", "aborts", "warnings", "running",
              "stdout", "stderr", "user", "debug"]

    level_aliases = {
        "output": ["stdout", "stderr"],
        "everything": ["warnings", "running", "user", "output"]
    }

    lhide = level_aliases["everything"]
    lshow = []

    if args.verbose == 1:
        lshow = levels[:3]
        lhide = levels[3:]
    elif args.verbose == 2:
        lshow = levels[:4]
        lhide = levels[4:]
    elif args.verbose >= 3 or args.debug:
        lshow = levels
        lhide = []

#   fabcmd += " --fabfile {4}/fabfile.py \
# setup_env:confdir={0},packages={1},templates={2},cluster_name={3},\
# autoconf={5},disable_colors={6},key_inject={7} \
# ".format(args.confdir, env.packages, env.templates, args.cluster_name,
#          env.lib, args.autoconf, args.disable_colors, args.key_inject)

    if nodes:
        ips = [env.nodes_info[n].ip for n in nodes]

    fabfile.setup_env(args, env)
    with settings(hide(*lhide), show(*lshow)):
        print " ".join(actions)
        for a in actions:
            fn = getattr(fabfile, a)
            if nodes:
                execute(fn, hosts=ips)
            else:
                execute(fn)


def cluster(args, env):
    for hostname, mac in env.node2mac.iteritems():
        launch_vm(args, env, hostname, mac)

    time.sleep(30)
    os.system("reset")


def launch_vm(args, env, hostname, mac):
    check_pidfile("%s/%s.pid" % (env.run, hostname))

    print("Launching cluster node {0}..".format(hostname))
    os.environ["BRIDGE"] = env.bridge
    if args.vnc:
        graphics = "-vnc :{0}".format(random.randint(1, 1000))
    else:
        graphics = "-nographic"

    disks = """ \
-drive file={0}/{1}.disk0,format=raw,if=none,id=drive0,snapshot=on \
-device virtio-blk-pci,drive=drive0,id=virtio-blk-pci.0 \
""".format(env.images, env.os)

    if ast.literal_eval(env.create_extra_disk):
        disks += """ \
-drive file={0}/{1}.disk1,format=raw,if=none,id=drive1,snapshot=on \
-device virtio-blk-pci,drive=drive1,id=virtio-blk-pci.1 \
""".format(env.images, env.os)

    ifup = env.lib + "/ifup"
    nics = """ \
-netdev tap,id=netdev0,script={0},downscript=no \
-device virtio-net-pci,mac={1},netdev=netdev0,id=virtio-net-pci.0 \
-netdev tap,id=netdev1,script={0},downscript=no \
-device virtio-net-pci,mac={2},netdev=netdev1,id=virtio-net-pci.1 \
-netdev tap,id=netdev2,script={0},downscript=no \
-device virtio-net-pci,mac={3},netdev=netdev2,id=virtio-net-pci.2 \
""".format(ifup, mac, random_mac(), random_mac())

    cmd = """
/usr/bin/kvm -name {0} -pidfile {1}/{0}.pid -balloon virtio -daemonize \
-monitor unix:{1}/{0}.monitor,server,nowait -usbdevice tablet -boot c \
{2} \
{3} \
-m {4} -smp {5} {6} \
""".format(hostname, env.run, disks, nics, args.mem, args.smp, graphics)
    print cmd
    os.system(cmd)


def dnsmasq(args, env):
    check_pidfile(env.run + "/dnsmasq.pid")
    cmd = "dnsmasq --pid-file={0}/dnsmasq.pid --conf-file={1}/conf-file"\
        .format(env.run, env.dns)
    os.system(cmd)


def get_packages(args, env):
    if env.package_url:
        os.system("rm {0}/*.deb".format(env.packages))
        os.system("wget -r --level=1 -nH --no-parent --cut-dirs=4 {0} -P {1}"
                  .format(env.package_url, env.packages))


def parse_options():
    parser = argparse.ArgumentParser()

    # Directories to load/store config
    parser.add_argument("-c", dest="confdir",
                        default="/etc/snf-deploy",
                        help="Directory to find default configuration")
    parser.add_argument("-t", "--templates-dir", dest="templatesdir",
                        default=None,
                        help="Directory to find templates. Overrides"
                             " the one found in the deploy.conf file")
    parser.add_argument("-s", "--state-dir", dest="statedir",
                        default=None,
                        help="Directory to store current state. Overrides"
                             " the one found in the deploy.conf")
    parser.add_argument("--dry-run", dest="dry_run",
                        default=False, action="store_true",
                        help="Do not execute or write anything.")
    parser.add_argument("-v", dest="verbose",
                        default=0, action="count",
                        help="Increase verbosity.")
    parser.add_argument("-d", dest="debug",
                        default=False, action="store_true",
                        help="Debug mode")
    parser.add_argument("--autoconf", dest="autoconf",
                        default=False, action="store_true",
                        help="In case of all in one auto conf setup")

    # virtual cluster related options
    parser.add_argument("--mem", dest="mem",
                        default=2024,
                        help="Memory for every virtual node")
    parser.add_argument("--smp", dest="smp",
                        default=1,
                        help="Virtual CPUs for every virtual node")
    parser.add_argument("--vnc", dest="vnc",
                        default=False, action="store_true",
                        help="Whether virtual nodes will have a vnc "
                             "console or not")
    parser.add_argument("--force", dest="force",
                        default=False, action="store_true",
                        help="Force things (creation of key pairs"
                             " do not abort execution if something fails")

    parser.add_argument("-i", "--ssh-key", dest="ssh_key",
                        default=None,
                        help="Path of an existing ssh key to use")

    parser.add_argument("--no-key-inject", dest="key_inject",
                        default=True, action="store_false",
                        help="Whether to inject ssh key pairs to hosts")

    # backend related options
    parser.add_argument("--cluster-name", dest="cluster_name",
                        default="ganeti1",
                        help="The cluster name in ganeti.conf")

    # backend related options
    parser.add_argument("--cluster-node", dest="cluster_node",
                        default=None,
                        help="The node to add to the existing cluster")

    # options related to custom setup
    parser.add_argument("--component", dest="component",
                        default=None,
                        help="The component class")

    parser.add_argument("--method", dest="method",
                        default=None,
                        help="The component method")

    parser.add_argument("--role", dest="role",
                        default=None,
                        help="The target node's role")

    parser.add_argument("--node", dest="node",
                        default="node1",
                        help="The target node")

    # available commands
    parser.add_argument("command", type=str,
                        choices=["packages", "vcluster", "cleanup",
                                 "run", "test", "all", "keygen", "ganeti"],
                        help="Run on of the supported deployment commands")

    # available actions for the run command
    parser.add_argument("actions", type=str, nargs="*",
                        help="Run one or more of the supported subcommands")

    # disable colors in terminal
    parser.add_argument("--disable-colors", dest="disable_colors",
                        default=False, action="store_true",
                        help="Disable colors in terminal")

    return parser.parse_args()


def get_actions(*args):
    actions = {
        "backend": [
            "setup_master_role",
            "setup_ganeti_role",
            "add_ganeti_backend",
        ],
        "ganeti": [
            "setup_ns_role",
            "setup_nfs_role",
            "setup_master_role",
            "setup_ganeti_role",
        ],
        "all": [
            "setup_ns_role",
            "setup_nfs_role",
            "setup_db_role",
            "setup_mq_role",
            "setup_astakos_role",
            "setup_pithos_role",
            "setup_cyclades_role",
            "setup_cms_role",
            "setup_master_role",
            "setup_ganeti_role",
            "setup_stats_role",
            "set_default_quota",
            "add_ganeti_backend",
            "add_public_networks",
            "add_synnefo_user",
            "activate_user",
            "setup_client_role",
            "add_image",
        ],

    }

    ret = []
    for x in args:
        ret += actions[x]

    return ret


def must_create_keys(env):
    """Check if we ssh keys already exist

    """
    d = os.path.join(env.templates, "root/.ssh")
    auth_keys_exists = os.path.exists(os.path.join(d, "authorized_keys"))
    dsa_exists = os.path.exists(os.path.join(d, "id_dsa"))
    dsa_pub_exists = os.path.exists(os.path.join(d, "id_dsa.pub"))
    rsa_exists = os.path.exists(os.path.join(d, "id_rsa"))
    rsa_pub_exists = os.path.exists(os.path.join(d, "id_rsa.pub"))
    # If any of the above doesn't exist return True
    return not (dsa_exists and dsa_pub_exists
                and rsa_exists and rsa_pub_exists
                and auth_keys_exists)


def do_create_keys(args, env):
    d = os.path.join(env.templates, "root/.ssh")
    # Create dir if it does not exist
    if not os.path.exists(d):
        os.makedirs(d)
    a = os.path.join(d, "authorized_keys")
    # Delete old keys
    for filename in os.listdir(d):
        os.remove(os.path.join(d, filename))
    # Generate new keys
    for t in ("dsa", "rsa"):
        f = os.path.join(d, "id_" + t)
        cmd = 'ssh-keygen -q -t {0} -f {1} -N ""'.format(t, f)
        os.system(cmd)
        cmd = 'cat {0}.pub >> {1}'.format(f, a)
        os.system(cmd)


def must_create_ddns_keys(env):
    d = os.path.join(env.templates, "root/ddns")
    # Create dir if it does not exist
    if not os.path.exists(d):
        os.makedirs(d)
    key_exists = glob.glob(os.path.join(d, "Kddns*key"))
    private_exists = glob.glob(os.path.join(d, "Kddns*private"))
    bind_key_exists = os.path.exists(os.path.join(d, "ddns.key"))
    return not (key_exists and private_exists and bind_key_exists)


def find_ddns_key_files(env):
    d = os.path.join(env.templates, "root/ddns")
    keys = glob.glob(os.path.join(d, "Kddns*"))
    # Here we must have a key!
    return map(os.path.basename, keys)


def do_create_ddns_keys(args, env):
    d = os.path.join(env.templates, "root/ddns")
    if not os.path.exists(d):
        os.mkdir(d)
    for filename in os.listdir(d):
        os.remove(os.path.join(d, filename))
    cmd = """
dnssec-keygen -a HMAC-MD5 -b 128 -K {0} -r /dev/urandom -n USER DDNS_UPDATE
key=$(cat {0}/Kddns_update*.key | awk '{{ print $7 }}')
cat > {0}/ddns.key <<EOF
key DDNS_UPDATE {{
        algorithm HMAC-MD5.SIG-ALG.REG.INT;
        secret "$key";
}};
EOF
""".format(d)
    os.system(cmd)


def main():
    args = parse_options()

    conf = Conf(args)
    env = Env(conf)
    env.status = Status(env)

    create_dir(env.run, False)
    create_dir(env.dns, False)

    # Check if there are keys to use
    if args.command == "keygen":
        if must_create_keys(env) or args.force:
            do_create_keys(args, env)
        else:
            print "ssh keys found. To re-create them use --force"
        if must_create_ddns_keys(env) or args.force:
            do_create_ddns_keys(args, env)
        else:
            print "ddns keys found. To re-create them use --force"
        return 0
    else:
        if ((args.key_inject and not args.ssh_key and
             must_create_keys(env)) or must_create_ddns_keys(env)):
            print "No ssh/ddns keys to use. Run `snf-deploy keygen' first."
            return 1
        env.ddns_keys = find_ddns_key_files(env)
        env.ddns_private_key = "/root/ddns/" + env.ddns_keys[0]

    if args.command == "test":
        conf.print_config()

    if args.command == "cleanup":
        cleanup(args, env)

    if args.command == "packages":
        create_dir(env.packages, True)
        get_packages(args, env)

    if args.command == "vcluster":
        image(args, env)
        network(args, env)
        create_dnsmasq_files(args, env)
        dnsmasq(args, env)
        cluster(args, env)

    if args.command == "backend":
        actions = get_actions("backend")
        fabcommand(args, env, actions)

    if args.command == "ganeti":
        actions = get_actions("ganeti")
        fabcommand(args, env, actions)

    if args.command == "all":
        actions = get_actions("all")
        fabcommand(args, env, actions)

    if args.command == "run":
        if not args.actions:
            print_available_actions(args.command)
        else:
            fabcommand(args, env, args.actions)

    return 0

if __name__ == "__main__":
    sys.exit(main())
