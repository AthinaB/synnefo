# Copyright 2014 GRNET S.A. All rights reserved.
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

import logging
import re
from django.views.decorators.csrf import csrf_exempt
from collections import OrderedDict

from actions import AdminAction, nop

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.functions import send_plain as send_email

from synnefo.logic import servers as servers_backend

templates = {
    'index': 'admin/vm_index.html',
    'details': 'admin/vm_details.html',
}


class VMAction(AdminAction):

    """Class for actions on VMs. Derived from AdminAction.

    Pre-determined Attributes:
        target:        vm
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='vm', f=f, **kwargs)


def vm_suspend(vm):
    """Suspend a VM."""
    vm.suspended = True
    vm.save()


def vm_suspend_release(vm):
    """Release previous VM suspension."""
    vm.suspended = False
    vm.save()


def generate_actions():
    """Create a list of actions on users.

    The actions are: start/shutdown, restart, destroy,
                     suspend/release, reassign, contact
    """
    actions = OrderedDict()

    actions['start'] = VMAction(name='Start', f=servers_backend.start,
                                severity='trivial')

    actions['shutdown'] = VMAction(name='Shutdown', f=servers_backend.stop,
                                   severity='big')

    actions['restart'] = VMAction(name='Restart', f=servers_backend.reboot,
                                  severity='big')

    actions['destroy'] = VMAction(name='Destroy', f=servers_backend.destroy,
                                  severity='irreversible')

    actions['suspend'] = VMAction(name='Suspend', f=vm_suspend, severity='big')

    actions['release'] = VMAction(name='Release suspension',
                                  f=vm_suspend_release, severity='trivial')

    actions['reassign'] = VMAction(name='Reassign', f=nop, severity='big')

    actions['contact'] = VMAction(name='Send e-mail', f=send_email,
                                  severity='trivial')
    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    vm = VirtualMachine.objects.get(pk=id)
    actions = generate_actions()
    logging.info("Op: %s, vm: %s, function", op, vm.pk, actions[op].f)

    if op == 'restart':
        actions[op].f(vm, "SOFT")
    elif op == 'contact':
        user = AstakosUser.objects.get(uuid=vm.userid)
        actions[op].f(user, request.POST['text'])
    else:
        actions[op].f(vm)


def index(request):
    """Index view for Cyclades VMs."""
    context = {}
    context['action_dict'] = generate_actions()

    all = VirtualMachine.objects.all()
    logging.info("These are the VMs %s", all)

    user_context = {
        'item_list': all,
        'item_type': 'vm',
    }

    context.update(user_context)
    return context


def details(request, query):
    """Details view for Astakos users."""
    try:
        id = query.translate(None, 'vm-')
    except Exception:
        id = query

    vm = VirtualMachine.objects.get(pk=int(id))
    users = [AstakosUser.objects.get(uuid=vm.userid)]
    projects = [Project.objects.get(uuid=vm.project)]
    networks = vm.nics.all()

    context = {
        'main_item': vm,
        'main_type': 'vm',
        'associations_list': [
            (users, 'user'),
            (projects, 'project'),
            (networks, 'network'),
        ]
    }

    return context