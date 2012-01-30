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

# Utility functions

from synnefo.db.models import VirtualMachine
from synnefo.logic import credits

from django.conf import settings

def id_from_instance_name(name):
    """Returns VirtualMachine's Django id, given a ganeti machine name.

    Strips the ganeti prefix atm. Needs a better name!

    """
    if not str(name).startswith(settings.BACKEND_PREFIX_ID):
        raise VirtualMachine.InvalidBackendIdError(str(name))
    ns = str(name).replace(settings.BACKEND_PREFIX_ID, "", 1)
    if not ns.isdigit():
        raise VirtualMachine.InvalidBackendIdError(str(name))

    return int(ns)

def get_rsapi_state(vm):
    """Returns the API state for a virtual machine

    The API state for an instance of VirtualMachine is derived as follows:

    * If the deleted flag has been set, it is "DELETED".
    * Otherwise, it is a mapping of the last state reported by Ganeti
      (vm.operstate) through the RSAPI_STATE_FROM_OPER_STATE dictionary.

      The last state reported by Ganeti is set whenever Ganeti reports
      successful completion of an operation. If Ganeti says an OP_INSTANCE_STARTUP
      operation succeeded, vm.operstate is set to "STARTED".

    * To support any transitional states defined by the API (only REBOOT for the time
      being) this mapping is amended with information reported by Ganeti regarding
      any outstanding operation. If an OP_INSTANCE_STARTUP had succeeded previously
      and an OP_INSTANCE_REBOOT has been reported as in progress, the API state is
      "REBOOT".

    """
    try:
        r = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE[vm.operstate]
    except KeyError:
        return "UNKNOWN"
    # A machine is DELETED if the deleted flag has been set
    if vm.deleted:
        return "DELETED"
    # A machine is in REBOOT if an OP_INSTANCE_REBOOT request is in progress
    if r == 'ACTIVE' and vm.backendopcode == 'OP_INSTANCE_REBOOT' and \
        vm.backendjobstatus in ('queued', 'waiting', 'running'):
        return "REBOOT"
    return r

def update_state(vm, new_operstate):
    """Wrapper around updates of the VirtualMachine.operstate field"""

    # Call charge() unconditionally before any change of
    # internal state.
    credits.charge(vm)
    vm.operstate = new_operstate
