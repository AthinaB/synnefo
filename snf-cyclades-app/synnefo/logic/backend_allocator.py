# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

import logging
import datetime
from django.utils import importlib

from django.conf import settings
from synnefo.db.models import Backend
from synnefo.logic import backend as backend_mod

log = logging.getLogger(__name__)


class BackendAllocator():
    """Wrapper class for instance allocation.

    """
    def __init__(self):
        self.strategy_mod =\
            importlib.import_module(settings.BACKEND_ALLOCATOR_MODULE)

    def allocate(self, userid, flavor):
        """Allocate a vm of the specified flavor to a backend.

        Warning!!: An explicit commit is required after calling this function,
        in order to release the locks acquired by the get_available_backends
        function.

        """

        backend = None
        backend = get_backend_for_user(userid)
        if backend:
            return backend

        # Get the size of the vm
        disk = flavor_disk(flavor)
        ram = flavor.ram
        cpu = flavor.cpu
        vm = {'ram': ram, 'disk': disk, 'cpu': cpu}

        log.debug("Allocating VM: %r", vm)

        # Get available backends
        available_backends = get_available_backends(flavor)

        # Refresh backends, if needed
        refresh_backends_stats(available_backends)

        if not available_backends:
            return None

        # Find the best backend to host the vm, based on the allocation
        # strategy
        backend = self.strategy_mod.allocate(available_backends, vm)

        log.info("Allocated VM %r, in backend %s", vm, backend)

        # Reduce the free resources of the selected backend by the size of
        # the vm
        reduce_backend_resources(backend, vm)

        return backend


def get_available_backends(flavor):
    """Get the list of available backends that can host a new VM of a flavor.

    The list contains the backends that are online and that have enabled
    the disk_template of the new VM.

    Also, if the new VM will be automatically connected to a public network,
    the backends that do not have an available public IPv4 address are
    excluded.

    """
    disk_template = flavor.disk_template
    # Ganeti knows only the 'ext' disk template, but the flavors disk template
    # includes the provider.
    if disk_template.startswith("ext_"):
        disk_template = "ext"

    backends = Backend.objects.select_for_update()
    backends = backends.filter(offline=False, drained=False,
                               disk_templates__contains=disk_template)
    backends = list(backends)
    return backends


def flavor_disk(flavor):
    """ Get flavor's 'real' disk size

    """
    if flavor.disk_template == 'drbd':
        return flavor.disk * 1024 * 2
    else:
        return flavor.disk * 1024


def reduce_backend_resources(backend, vm):
    """ Conservatively update the resources of a backend.

    Reduce the free resources of the backend by the size of the of the vm that
    will host. This is an underestimation of the backend capabilities.

    """

    new_mfree = backend.mfree - vm['ram']
    new_dfree = backend.dfree - vm['disk']
    backend.mfree = 0 if new_mfree < 0 else new_mfree
    backend.dfree = 0 if new_dfree < 0 else new_dfree
    backend.pinst_cnt += 1

    backend.save()


def refresh_backends_stats(backends):
    """ Refresh the statistics of the backends.

    Set db backend state to the actual state of the backend, if
    BACKEND_REFRESH_MIN time has passed.

    """

    now = datetime.datetime.now()
    delta = datetime.timedelta(minutes=settings.BACKEND_REFRESH_MIN)
    for b in backends:
        if now > b.updated + delta:
            log.debug("Updating resources of backend %r. Last Updated %r",
                      b, b.updated)
            backend_mod.update_backend_resources(b)


def get_backend_for_user(userid):
    """Find fixed Backend for user based on BACKEND_PER_USER setting."""

    backend = settings.BACKEND_PER_USER.get(userid)

    if not backend:
        return None

    try:
        try:
            backend_id = int(backend)
            return Backend.objects.get(id=backend_id)
        except ValueError:
            pass

        backend_name = str(backend)
        return Backend.objects.get(clustername=backend_name)
    except Backend.DoesNotExist:
        log.error("Invalid backend %s for user %s", backend, userid)
