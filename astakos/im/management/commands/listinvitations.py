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

from astakos.im.models import Invitation


class Command(BaseCommand):
    help = "List users"
    
    option_list = BaseCommand.option_list + (
        make_option('-c',
            action='store_true',
            dest='csv',
            default=False,
            help="Use pipes to separate values"),
        )
    
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")
        
        invitations = Invitation.objects.all()
        
        labels = ('id', 'email', 'real name', 'code', 'used', 'consumed')
        columns = (3, 24, 24, 20, 4, 8)
        
        if not options['csv']:
            line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')
        
        for invitation in invitations:
            id = str(invitation.id)
            code = str(invitation.code)
            used = 'YES' if invitation.is_accepted else 'NO'
            consumed = 'YES' if invitation.is_consumed else 'NO'
            fields = (id, invitation.username, invitation.realname,
                      code, used, consumed)
            
            if options['csv']:
                line = '|'.join(fields)
            else:
                line = ' '.join(f.rjust(w) for f, w in zip(fields, columns))
            
            self.stdout.write(line.encode('utf8') + '\n')
