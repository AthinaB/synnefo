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
from synnefo_admin.admin.utils import filter_owner_name


def filter_vm_id(queryset, query):
    # FIXME: This should change
    prefix = 'snf-'
    query = query.replace(prefix, '')
    if not query.isdigit():
        return queryset
    return queryset.filter(id__contains=query)


class VMFilterSet(django_filters.FilterSet):

    """A collection of filters for VMs.

    This filter collection is based on django-filter's FilterSet.
    """

    id = django_filters.CharFilter(label='VM ID', action=filter_vm_id)
    name = django_filters.CharFilter(label='Name', lookup_type='icontains')
    owner_name = django_filters.CharFilter(label='Owner Name',
                                           action=filter_owner_name)
    userid = django_filters.CharFilter(label='Owner UUID',
                                       lookup_type='icontains')
    imageid = django_filters.CharFilter(label='Image UUID',
                                        lookup_type='icontains')
    operstate = django_filters.MultipleChoiceFilter(
        label='Status', name='operstate', choices=VirtualMachine.OPER_STATES)

    class Meta:
        model = VirtualMachine
        fields = ('id', 'operstate', 'name', 'owner_name', 'userid', 'imageid',
                  'suspended',)
