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

import functools
import logging
import inspect
from importlib import import_module
from operator import or_

from django.db.models import Q
from django.views.decorators.gzip import gzip_page
from django.template import Context, Template
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.conf import settings

from synnefo_admin import admin_settings
from synnefo.util import units
from astakos.im.models import AstakosUser

from .actions import get_allowed_actions, get_permitted_actions
logger = logging.getLogger(__name__)


def admin_log(request, *argc, **kwargs):
    caller_name = inspect.stack()[1][3]
    s = "User: %s, " % request.user['access']['user']['name']
    s += "View: %s, " % caller_name

    for key, value in kwargs.iteritems():
        s += "%s: %s, " % (key.capitalize(), value)

    logging.info(s)


def conditionally_gzip_page(func):
    """Decorator to gzip response of unpaginated json requests."""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.REQUEST['iDisplayLength'] > 0:
            return func(request, *args, **kwargs)
        else:
            return gzip_page(func)(request, *args, **kwargs)
    return wrapper


def is_resource_useful(resource, project_limit):
    """Simple function to check if the resource is useful to show.

    Values that have infinite or zero limits are discarded.
    """
    displayed_limit = units.show(project_limit, resource.unit)
    if project_limit == 0 or not resource.uplimit or displayed_limit == 'inf':
        return False
    return True


def filter_name(queryset, search):
    """Filter by name using keywords.

    Since there is no single name field, we will search both in first_name,
    last_name fields.
    """
    fields = ['first_name', 'last_name']
    for term in search.split():
        criterions = (Q(**{'%s__icontains' % field: term}) for field in fields)
        qor = reduce(or_, criterions)
        queryset = queryset.filter(qor)
    return queryset


def flatten(l):
    return [item for sublist in l for item in sublist]


def filter_owner_name(queryset, search):
    """Filter by first name / last name of the owner.

    This filter is a bit tricky, so an explanation is due.

    The main purpose of the filter is to:
    a) Use the `filter_name` function of `users` module to find all
       the users whose name matches the search query.
    b) Use the UUIDs of the filtered users to retrieve all the entities that
       belong to them.

    What we should have in mind is that the (a) query can be a rather expensive
    one. However, the main issue here is the (b) query. For this query, a
    naive approach would be to use Q objects like so:

        Q(userid=1ae43...) | Q(userid=23bc...) | Q(userid=7be8...) | ...

    Straightforward as it may be, Django will not optimize the above expression
    into one operation but will query the database recursively. In practice, if
    the first query hasn't narrowed down the users to less than a thousand,
    this query will surely blow the stack of the database thread.

    Given that all Q objects refer to the same database field, we can bypass
    them and use the "__in" operator.  With "__in" we can pass a list of values
    (uuids in our case) as a filter argument. Moreover, we can simplify things
    a bit more by passing the queryset of (a) as the argument of "__in".  In
    Postgres, this will create a subquery, which nullifies the need to evaluate
    the results of (a) in memory and then pass them to (b).

    Warning: Querying a database using a subquery for another database has not
    been tested yet.
    """
    # Leave if no name has been given
    if not search:
        return queryset
    # Find all the users that match the requested search term
    users = filter_name(AstakosUser.objects.all(), search).\
        values_list('uuid')
    users = flatten(users)
    # Get the related entities with the UUIDs of these users
    return queryset.filter(userid__in=users).distinct()


def filter_email(queryset, search):
    """Filter by email."""
    queryset = queryset.filter(email__icontains=search)
    return queryset


def filter_owner_email(queryset, search):
    # Leave if no name has been given
    if not search:
        return queryset
    # Find all the users that match the requested search term
    users = filter_email(AstakosUser.objects.all(), search).\
        values_list('uuid')
    users = flatten(users)
    # Get the related entities with the UUIDs of these users
    return queryset.filter(userid__in=users).distinct()


def filter_id(field):
    def _filter_id(qs, query):
        if not query:
            return qs
        return qs.filter(**{"%s__icontains" % field: int(query)})

    return _filter_id


def filter_vm_id(field):
    def _filter_vm_id(qs, query):
        query = str(query)
        lookup_type = 'contains'
        prefix = settings.BACKEND_PREFIX_ID
        if query.startswith(prefix):
            query = query.replace(prefix, '')
            lookup_type = 'startswith'
        if not query.isdigit():
            return qs
        return qs.filter(**{"%s__%s" % (field, lookup_type): int(query)})

    return _filter_vm_id


def get_actions(target, user=None, inst=None):
    """Generic function for getting actions for various targets.

    Note: this function will import the action module for the target, which
    means that it may be slow.
    """
    if target in ['quota', 'nic', 'ip_log']:
        return None

    mod = import_module('synnefo_admin.admin.%ss.actions' % target)
    actions = mod.cached_actions
    if inst:
        return get_allowed_actions(actions, inst, user)
    else:
        return get_permitted_actions(actions, user)


def update_actions_rbac(actions):
    """Add allowed groups to actions dictionary from settings.

    Read the settings file to find the allowed groups for this action.
    """
    for op, action in actions.iteritems():
        target = action.target
        groups = []
        try:
            groups = admin_settings.ADMIN_RBAC[target][op]
        except KeyError:
            pass

        action.allowed_groups = groups


def render_email(request, user):
    """Render an email and return its subject and body.

    This function takes as arguments a QueryDict and a user. The user will
    serve as the target of the mail. The QueryDict should contain a `text` and
    `subject` attribute that will be used as the body and subject of the mail
    respectively.

    The email can optionally be customized with user information. If the user
    has provided any one of the following variables:

        {{ full_name }}, {{ first_name }}, {{ last_name }}, {{ email }}

    then they will be rendered appropriately.
    """
    subject = request['subject']
    c = Context({'full_name': user.realname,
                 'first_name': user.first_name,
                 'last_name': user.last_name,
                 'email': user.email, })
    t = Template(request['text'])
    body = t.render(c)
    #logging.info("Subject is %s, body is %s", subject, body)
    return subject, body


def create_details_href(type, name, id):
    name = escape(name)
    """Create an href (name + url) for the details page of an item."""
    url = reverse('admin-details', args=[type, id])
    if type == 'user':
        href = '<a href=%s>%s (%s)</a>' % (url, name, id)
    elif type == 'ip':
        href = '<a href=%s>%s</a>' % (url, name)
    else:
        href = '<a href=%s>%s (id:%s)</a>' % (url, name, id)
    return href


def filter_distinct(assoc):
    if assoc.qs:
        assoc.qs = assoc.qs.distinct()


def exclude_deleted(assoc):
    """Exclude deleted items."""
    if admin_settings.ADMIN_SHOW_DELETED_ASSOCIATED_ITEMS or not assoc.qs:
        return

    if assoc.type in ['vm', 'volume', 'network', 'ip']:
        assoc.qs = assoc.qs.exclude(deleted=True)
    elif assoc.type == 'nic':
        assoc.qs = assoc.qs.exclude(machine__deleted=True)

    assoc.deleted = assoc.total - assoc.qs.count()


def limit_shown(assoc):
    limit = admin_settings.ADMIN_LIMIT_ASSOCIATED_ITEMS_PER_CATEGORY
    assoc.items = assoc.items[:limit]
    assoc.showing = assoc.count_items()


def customize_details_context(context):
    """Perform generic customizations on the detail context."""
    for assoc in context['associations_list']:
        filter_distinct(assoc)
        exclude_deleted(assoc)
        limit_shown(assoc)
