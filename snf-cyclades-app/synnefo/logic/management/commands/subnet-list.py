# Copyright 2013 GRNET S.A. All rights reserved.
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
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS"" AND ANY EXPRESS
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

from snf_django.management.commands import ListCommand, CommandError
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from synnefo.db.models import Subnet

from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List subnets"

    option_list = ListCommand.option_list + (
        make_option(
            "--ipv4",
            action="store_true",
            dest="ipv4",
            default=False,
            help="List only IPv4 subnets"),
        make_option(
            "--ipv6",
            action="store_true",
            dest="ipv6",
            default=False,
            help="List only IPv6 subnets"),
        make_option(
            "--dhcp",
            action="store_true",
            dest="dhcp",
            default=False,
            help="List only subnets that have DHCP/SLAC enabled"),
        make_option(
            "--public",
            action="store_true",
            dest="public",
            default=False,
            help="List only public subnets"),
    )

    object_class = Subnet
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN
    deleted_field = "deleted"

    FIELDS = {
        "id": ("id", "ID of the subnet"),
        "network": ("network_id", "ID of the network the subnet belongs to"),
        "name": ("name", "Name of the subnet"),
        "user.uuid": ("userid", "The UUID of the subnet's owner"),
        "cidr": ("cidr", "The CIDR of the subnet"),
        "ipversion": ("ipversion", "The IP version of the subnet"),
        "gateway": ("gateway", "The gateway IP of the subnet"),
        "dhcp": ("dhcp", "DHCP flag of the subnet"),
        "public": ("public", "Public flag of the subnet"),
    }

    fields = ["id", "network", "name", "user.uuid", "cidr", "ipversion",
              "gateway", "dhcp", "public"]

    def handle_args(self, *args, **options):
        if options["ipv4"] and options["ipv6"]:
            raise CommandError("Use either --ipv4 or --ipv6, not both")

        if options["ipv4"]:
            self.filters["ipversion"] = 4

        if options["ipv6"]:
            self.filters["ipversion"] = 6

        if options["dhcp"]:
            self.filters["dhcp"] = True

        if options["public"]:
            self.filters["public"] = True
