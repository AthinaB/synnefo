# Copyright 2012-2014 GRNET S.A. All rights reserved.
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


from synnefo.settings import BACKEND_PREFIX_ID, DEBUG, EXCHANGE_GANETI

try:
    prefix = BACKEND_PREFIX_ID.split('-')[0]
except TypeError, IndexError:
    raise Exception("Invalid BACKEND_PREFIX_ID")

# EXCHANGES
EXCHANGES = (EXCHANGE_GANETI,)


# QUEUES
QUEUE_OP = "%s-events-op" % prefix
QUEUE_NETWORK = "%s-events-network" % prefix
QUEUE_PROGRESS = "%s-events-progress" % prefix
QUEUE_CLUSTER = "%s-events-cluster" % prefix


QUEUES = (QUEUE_OP,
          QUEUE_NETWORK,
          QUEUE_PROGRESS,
          QUEUE_CLUSTER)

# ROUTING KEYS
# notifications of type "ganeti-op-status"
KEY_OP = 'ganeti.%s.event.op' % prefix
# notifications of type "ganeti-network-status"
KEY_NETWORK = 'ganeti.%s.event.network' % prefix
# notifications of type "ganeti-create-progress"
KEY_PROGRESS = 'ganeti.%s.event.progress' % prefix
KEY_CLUSTER = 'ganeti.event.cluster'

# BINDINGS:
BINDINGS = (
    # Queue           # Exchange        # RouteKey    # Handler
    (QUEUE_OP,        EXCHANGE_GANETI,  KEY_OP,       'update_db'),
    (QUEUE_NETWORK,   EXCHANGE_GANETI,  KEY_NETWORK,  'update_network'),
    (QUEUE_PROGRESS,  EXCHANGE_GANETI,  KEY_PROGRESS, 'update_build_progress'),
    (QUEUE_CLUSTER,   EXCHANGE_GANETI,  KEY_CLUSTER,  'update_cluster'),
)


## Extra for DEBUG:
if DEBUG is True:
    # Debug queue, retrieves all messages
    QUEUE_DEBUG = "%s-debug" % prefix
    QUEUES += (QUEUE_DEBUG,)
    BINDINGS += ((QUEUE_DEBUG, EXCHANGE_GANETI, "#", "dummy_proc"),)


def convert_queue_to_dead(queue):
    """Convert the name of a queue to the corresponding dead-letter one"""
    return queue + "-dl"


def convert_exchange_to_dead(exchange):
    """Convert the name of an exchange to the corresponding dead-letter one"""
    return exchange + "-dl"


EVENTD_HEARTBEAT_ROUTING_KEY = "eventd.heartbeat"


def get_dispatcher_request_queue(hostname, pid):
    return "snf:dispatcher:%s:%s" % (hostname, pid)


def get_dispatcher_heartbeat_queue(hostname, pid):
    return "snf:dispatcher:heartbeat:%s:%s" % (hostname, pid)
