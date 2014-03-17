# Copyright 2012-2014 GRNET S.A. All rights reserved.
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

from django.core.management.base import CommandError
from optparse import make_option

from pithos.api.util import get_backend
from snf_django.management.commands import SynnefoCommand

import logging

logger = logging.getLogger(__name__)

CLIENTKEY = 'pithos'


class Command(SynnefoCommand):
    help = "Display unresolved commissions and trigger their recovery"

    option_list = SynnefoCommand.option_list + (
        make_option('--fix',
                    dest='fix',
                    action="store_true",
                    default=False,
                    help="Fix unresolved commissions"),
    )

    def handle_noargs(self, **options):
        b = get_backend()
        try:
            b.pre_exec()
            pending_commissions = b.astakosclient.get_pending_commissions()

            if pending_commissions:
                self.stdout.write(
                    "Unresolved commissions: %s\n" % pending_commissions
                )
            else:
                self.stdout.write("No unresolved commissions were found\n")
                return

            if options['fix']:
                to_accept = b.commission_serials.lookup(pending_commissions)
                to_reject = list(set(pending_commissions) - set(to_accept))
                response = b.astakosclient.resolve_commissions(
                    accept_serials=to_accept,
                    reject_serials=to_reject
                )
                accepted = response['accepted']
                rejected = response['rejected']
                failed = response['failed']
                self.stdout.write("Accepted commissions: %s\n" % accepted)
                self.stdout.write("Rejected commissions: %s\n" % rejected)
                self.stdout.write("Failed commissions:\n")
                for i in failed:
                    self.stdout.write('%s\n' % i)

                b.commission_serials.delete_many(accepted)
        except Exception, e:
            logger.exception(e)
            b.post_exec(False)
            raise CommandError(e)
        else:
            b.post_exec(True)
        finally:
            b.close()
