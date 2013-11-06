# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import get_backend, convert_api_faults
from snf_django.management.utils import parse_bool

from synnefo.db.models import Network, Backend
from synnefo.logic import networks
from synnefo.management import pprint

NETWORK_FLAVORS = Network.FLAVORS.keys()


class Command(BaseCommand):
    can_import_settings = True
    output_transaction = True

    help = "Create a new network"

    option_list = BaseCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            help="Name of network"),
        make_option(
            '--owner',
            dest='owner',
            help="The owner of the network"),
        make_option(
            '--subnet',
            dest='subnet',
            default=None,
            # required=True,
            help='Subnet of the network'),
        make_option(
            '--gateway',
            dest='gateway',
            default=None,
            help='Gateway of the network'),
        make_option(
            '--subnet6',
            dest='subnet6',
            default=None,
            help='IPv6 subnet of the network'),
        make_option(
            '--gateway6',
            dest='gateway6',
            default=None,
            help='IPv6 gateway of the network'),
        make_option(
            '--dhcp',
            dest='dhcp',
            default="False",
            choices=["True", "False"],
            metavar="True|False",
            help='Automatically assign IPs'),
        make_option(
            '--public',
            dest='public',
            action='store_true',
            default=False,
            help='Network is public'),
        make_option(
            '--flavor',
            dest='flavor',
            default=None,
            choices=NETWORK_FLAVORS,
            help='Network flavor. Choices: ' + ', '.join(NETWORK_FLAVORS)),
        make_option(
            '--mode',
            dest='mode',
            default=None,
            help="Overwrite flavor connectivity mode."),
        make_option(
            '--link',
            dest='link',
            default=None,
            help="Overwrite flavor connectivity link."),
        make_option(
            '--mac-prefix',
            dest='mac_prefix',
            default=None,
            help="Overwrite flavor connectivity MAC prefix"),
        make_option(
            '--tags',
            dest='tags',
            default=None,
            help='The tags of the Network (comma separated strings)'),
        make_option(
            '--floating-ip-pool',
            dest='floating_ip_pool',
            default="False",
            choices=["True", "False"],
            metavar="True|False",
            help="Use the network as a Floating IP pool. Floating IP pools"
                 " are created in all available backends."),
        make_option(
            "--backend-ids",
            dest="backend_ids",
            default=None,
            help="Comma seperated list of Ganeti backends IDs that the network"
                 " will be created. Only for public networks. Use 'all' to"
                 " create network in all available backends."),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options['name']
        subnet = options['subnet']
        gateway = options['gateway']
        subnet6 = options['subnet6']
        gateway6 = options['gateway6']
        backend_ids = options['backend_ids']
        public = options['public']
        flavor = options['flavor']
        mode = options['mode']
        link = options['link']
        mac_prefix = options['mac_prefix']
        tags = options['tags']
        userid = options["owner"]
        floating_ip_pool = parse_bool(options["floating_ip_pool"])
        dhcp = parse_bool(options["dhcp"])

        if name is None:
            name = ""
        if flavor is None:
            raise CommandError("flavor is required")

        if (subnet is None) and (subnet6 is None):
            raise CommandError("subnet or subnet6 is required")
        if subnet is None and gateway is not None:
            raise CommandError("Cannot use gateway without subnet")
        if subnet6 is None and gateway6 is not None:
            raise CommandError("Cannot use gateway6 without subnet6")
        if public and not (backend_ids or floating_ip_pool):
            raise CommandError("backend-ids is required")
        if not userid and not public:
            raise CommandError("'owner' is required for private networks")

        backends = []
        if backend_ids is not None:
            if backend_ids == "all":
                backends = Backend.objects.filter(offline=False)
            else:
                for backend_id in backend_ids.split(","):
                    try:
                        backend_id = int(backend_id)
                    except ValueError:
                        raise CommandError("Invalid backend-id: %s"
                                           % backend_id)
                    backend = get_backend(backend_id)
                    backends.append(backend)

        network = networks.create(userid=userid, name=name, flavor=flavor,
                                  subnet=subnet, gateway=gateway,
                                  subnet6=subnet6, gateway6=gateway6,
                                  dhcp=dhcp, public=public, mode=mode,
                                  link=link, mac_prefix=mac_prefix, tags=tags,
                                  floating_ip_pool=floating_ip_pool,
                                  backends=backends, lazy_create=False)

        self.stdout.write("Created network '%s' in DB:\n" % network)
        pprint.pprint_network(network, stdout=self.stdout)
        pprint.pprint_network_subnets(network, stdout=self.stdout)
