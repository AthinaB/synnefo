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

import logging
import re
from collections import OrderedDict

from operator import or_

from django.core.urlresolvers import reverse
from django.db.models import Q

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.user_utils import send_plain as send_email

from synnefo.logic import servers as servers_backend
from synnefo.logic.commands import validate_server_action

from eztables.views import DatatablesView

import django_filters

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)


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


def check_vm_action(action):
    if action == 'SUSPEND':
        return lambda vm: not vm.suspended
    elif action == 'RELEASE':
        return lambda vm: vm.suspended
    else:
        return lambda vm: validate_server_action(vm, action)


def generate_actions():
    """Create a list of actions on users.

    The actions are: start/shutdown, restart, destroy,
                     suspend/release, reassign, contact
    """
    actions = OrderedDict()

    actions['start'] = VMAction(name='Start', f=servers_backend.start,
                                c=check_vm_action('START'),
                                karma='good', reversible=True,
                                allowed_groups=['admin', 'superadmin'])

    actions['shutdown'] = VMAction(name='Shutdown', f=servers_backend.stop,
                                   c=check_vm_action('STOP'), karma='bad',
                                   reversible=True,
                                   allowed_groups=['admin', 'superadmin'])

    actions['reboot'] = VMAction(name='Reboot', f=servers_backend.reboot,
                                 c=check_vm_action('REBOOT'), karma='bad',
                                 reversible=True,
                                 allowed_groups=['admin', 'superadmin'])

    actions['resize'] = VMAction(name='Resize', f=noop,
                                 c=check_vm_action('RESIZE'), karma='neutral',
                                 reversible=False,
                                 allowed_groups=['superadmin'])

    actions['destroy'] = VMAction(name='Destroy', f=servers_backend.destroy,
                                  c=check_vm_action('DESTROY'), karma='bad',
                                  reversible=False,
                                  allowed_groups=['superadmin'])

    actions['connect'] = VMAction(name='Connect to network', f=noop,
                                  karma='good', reversible=True,
                                  allowed_groups=['superadmin'])

    actions['disconnect'] = VMAction(name='Disconnect from network', f=noop,
                                     karma='bad', reversible=True,
                                     allowed_groups=['superadmin'])

    actions['attach'] = VMAction(name='Attach IP', f=noop,
                                 c=check_vm_action('ADDFLOATINGIP'),
                                 karma='good', reversible=True,
                                 allowed_groups=['superadmin'])

    actions['detach'] = VMAction(name='Detach IP', f=noop,
                                 c=check_vm_action('REMOVEFLOATINGIP'),
                                 karma='bad', reversible=True,
                                 allowed_groups=['superadmin'])

    actions['suspend'] = VMAction(name='Suspend', f=vm_suspend,
                                  c=check_vm_action('SUSPEND'),
                                  karma='bad', reversible=True,
                                  allowed_groups=['admin', 'superadmin'])

    actions['release'] = VMAction(name='Release suspension',
                                  f=vm_suspend_release,
                                  c=check_vm_action('RELEASE'), karma='good',
                                  reversible=True,
                                  allowed_groups=['admin', 'superadmin'])

    actions['reassign'] = VMAction(name='Reassign to project', f=noop,
                                   karma='neutral', reversible=True,
                                   allowed_groups=['superadmin'])

    actions['change_owner'] = VMAction(name='Change owner', f=noop,
                                       karma='neutral', reversible=True,
                                       allowed_groups=['superadmin'])

    actions['contact'] = VMAction(name='Send e-mail', f=send_email,
                                  allowed_groups=['admin', 'superadmin'])

    return actions


def get_permitted_actions(user):
    actions = generate_actions()
    for key, action in actions.iteritems():
        if not action.is_user_allowed(user):
            actions.pop(key, None)
    return actions


def get_allowed_actions(vm):
    """Get a list of actions that can apply to a user."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(vm):
            allowed_actions.append(key)

    return allowed_actions