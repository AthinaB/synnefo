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

import json

from django.core.management.base import BaseCommand, CommandError

from synnefo.db.models import Backend, Network, BackendNetwork
from synnefo.util.rapi import GanetiApiError


class Command(BaseCommand):
    help = "Inspect a network on DB and Ganeti."

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a network ID.")
        try:
            net_id = int(args[0])
        except ValueError:
            raise CommandError("Invalid network ID.")

        try:
            net = Network.objects.get(id=net_id)
        except Network.DoesNotExist:
            raise CommandError("Network not found in DB.")

        sep = '-' * 80 + '\n'
        labels = ('name', 'backend-name', 'owner', 'subnet', 'gateway', 'max_prefix', 'link',
                  'public', 'dhcp', 'type', 'deleted', 'action')
        fields = (net.name, net.backend_id, str(net.userid), str(net.subnet), str(net.gateway),
                  str(net.mac_prefix), str(net.link), str(net.public),  str(net.dhcp),
                  str(net.type), str(net.deleted), str(net.action))

        self.stdout.write(sep)
        self.stdout.write('State of Network in DB\n')
        self.stdout.write(sep)
        for l, f in zip(labels, fields):
            self.stdout.write(l.ljust(20) + ': ' + f.ljust(20) + '\n')

        labels = ('Backend', 'State', 'Deleted', 'JobID', 'OpCode',
                  'JobStatus')
        for back_net in BackendNetwork.objects.filter(network=net):
            self.stdout.write('\n')
            fields = (back_net.backend.clustername, back_net.operstate,
                     str(back_net.deleted),  str(back_net.backendjobid),
                     str(back_net.backendopcode),
                     str(back_net.backendjobstatus))
            for l, f in zip(labels, fields):
                self.stdout.write(l.ljust(20) + ': ' + f.ljust(20) + '\n')
        self.stdout.write('\n')

        self.stdout.write(sep)
        self.stdout.write('State of Network in Ganeti\n')
        self.stdout.write(sep)

        for backend in Backend.objects.exclude(offline=True):
            client = backend.client
            try:
                g_net = client.GetNetwork(net.backend_id)
                self.stdout.write("Backend: %s\n" % backend.clustername)
                print json.dumps(g_net, indent=2)
                self.stdout.write(sep)
            except GanetiApiError as e:
                if e.code == 404:
                    self.stdout.write('Network does not exist in backend %s\n' %
                                      backend.clustername)
                else:
                    raise e
