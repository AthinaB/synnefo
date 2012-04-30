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
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from astakos.im.models import AstakosUser

class Command(BaseCommand):
    args = "<user ID>"
    help = "Modify a user's attributes"
    
    option_list = BaseCommand.option_list + (
        make_option('--invitations',
            dest='invitations',
            metavar='NUM',
            help="Update user's invitations"),
        make_option('--level',
            dest='level',
            metavar='NUM',
            help="Update user's level"),
        make_option('--password',
            dest='password',
            metavar='PASSWORD',
            help="Set user's password"),
        make_option('--renew-token',
            action='store_true',
            dest='renew_token',
            default=False,
            help="Renew the user's token"),
        make_option('--set-admin',
            action='store_true',
            dest='admin',
            default=False,
            help="Give user admin rights"),
        make_option('--set-noadmin',
            action='store_true',
            dest='noadmin',
            default=False,
            help="Revoke user's admin rights"),
        make_option('--set-active',
            action='store_true',
            dest='active',
            default=False,
            help="Change user's state to inactive"),
        make_option('--set-inactive',
            action='store_true',
            dest='inactive',
            default=False,
            help="Change user's state to inactive"),
        make_option('--add-group',
            dest='add-group',
            help="Add user group"),
        make_option('--delete-group',
            dest='delete-group',
            help="Delete user group"),
        )
    
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID")
        
        if args[0].isdigit():
            user = AstakosUser.objects.get(id=int( args[0]))
        else:
            raise CommandError("Invalid ID")
        
        if not user:
            raise CommandError("Unknown user")
        
        if options.get('admin'):
            user.is_superuser = True
        elif options.get('noadmin'):
            user.is_superuser = False
        
        if options.get('active'):
            user.is_active = True
        elif options.get('inactive'):
            user.is_active = False
        
        invitations = options.get('invitations')
        if invitations is not None:
            user.invitations = int(invitations)
        
        groupname = options.get('add-group')
        if groupname is not None:
            try:
                group = Group.objects.get(name=groupname)
                user.groups.add(group)
            except Group.DoesNotExist, e:
                raise CommandError("Group named %s does not exist." % groupname)
        
        groupname = options.get('delete-group')
        if groupname is not None:
            try:
                group = Group.objects.get(name=groupname)
                user.groups.remove(group)
            except Group.DoesNotExist, e:
                raise CommandError("Group named %s does not exist." % groupname)
        
        level = options.get('level')
        if level is not None:
            user.level = int(level)
        
        password = options.get('password')
        if password is not None:
            user.set_password(password)
        
        if options['renew_token']:
            user.renew_token()
        
        try:
            user.save()
        except ValidationError, e:
            raise CommandError(e)
