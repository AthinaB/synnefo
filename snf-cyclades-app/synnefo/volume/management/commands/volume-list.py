# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

#from optparse import make_option

from snf_django.management.commands import ListCommand
from synnefo.db.models import Volume
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from logging import getLogger
log = getLogger(__name__)


class Command(ListCommand):
    help = "List Volumes"

    option_list = ListCommand.option_list

    object_class = Volume
    deleted_field = "deleted"
    user_uuid_field = "userid"
    astakos_auth_url = ASTAKOS_AUTH_URL
    astakos_token = ASTAKOS_TOKEN

    FIELDS = {
        "id": ("id", "ID of the server"),
        "name": ("name", "Name of the server"),
        "user.uuid": ("userid", "The UUID of the server's owner"),
        "server_id": ("machine_id", ""),
        "source": ("source", ""),
        "status": ("status", ""),
        "created": ("created", "The date the server was created"),
        "deleted": ("deleted", "Whether the server is deleted or not"),
    }

    fields = ["id", "name", "user.uuid", "status", "source", "server_id"]
