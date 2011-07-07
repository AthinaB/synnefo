# Copyright 2011 GRNET S.A. All rights reserved.
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

from socket import getfqdn
from vncauthproxy.client import request_forwarding as request_vnc_forwarding

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api.faults import BadRequest, ServiceUnavailable
from synnefo.api.util import random_password, get_vm
from synnefo.db.models import NetworkInterface
from synnefo.logic import backend
from synnefo.logic.utils import get_rsapi_state


server_actions = {}
network_actions = {}


def server_action(name):
    '''Decorator for functions implementing server actions.
    `name` is the key in the dict passed by the client.
    '''

    def decorator(func):
        server_actions[name] = func
        return func
    return decorator

def network_action(name):
    '''Decorator for functions implementing network actions.
    `name` is the key in the dict passed by the client.
    '''

    def decorator(func):
        network_actions[name] = func
        return func
    return decorator


@server_action('changePassword')
def change_password(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)

    try:
        password = args['adminPass']
    except KeyError:
        raise BadRequest('Malformed request.')

    raise ServiceUnavailable('Changing password is not supported.')

@server_action('reboot')
def reboot(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)

    reboot_type = args.get('type', '')
    if reboot_type not in ('SOFT', 'HARD'):
        raise BadRequest('Malformed Request.')
    backend.reboot_instance(vm, reboot_type.lower())
    return HttpResponse(status=202)

@server_action('start')
def start(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    if args:
        raise BadRequest('Malformed Request.')
    backend.startup_instance(vm)
    return HttpResponse(status=202)

@server_action('shutdown')
def shutdown(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404)

    if args:
        raise BadRequest('Malformed Request.')
    backend.shutdown_instance(vm)
    return HttpResponse(status=202)

@server_action('rebuild')
def rebuild(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413)

    raise ServiceUnavailable('Rebuild not supported.')

@server_action('resize')
def resize(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)

    raise ServiceUnavailable('Resize not supported.')

@server_action('confirmResize')
def confirm_resize(request, vm, args):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)

    raise ServiceUnavailable('Resize not supported.')

@server_action('revertResize')
def revert_resize(request, vm, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       serverCapacityUnavailable (503),
    #                       overLimit (413),
    #                       resizeNotAllowed (403)

    raise ServiceUnavailable('Resize not supported.')

@server_action('console')
def get_console(request, vm, args):
    """Arrange for an OOB console of the specified type

    This method arranges for an OOB console of the specified type.
    Only consoles of type "vnc" are supported for now.

    It uses a running instance of vncauthproxy to setup proper
    VNC forwarding with a random password, then returns the necessary
    VNC connection info to the caller.
    """
    # Normal Response Code: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)

    console_type = args.get('type', '')
    if console_type != 'vnc':
        raise BadRequest('Type can only be "vnc".')

    # Use RAPI to get VNC console information for this instance
    if get_rsapi_state(vm) != 'ACTIVE':
        raise BadRequest('Server not in ACTIVE state.')

    if settings.TEST:
        console_data = {'kind': 'vnc', 'host': 'ganeti_node', 'port': 1000}
    else:
        console_data = backend.get_instance_console(vm)

    if console_data['kind'] != 'vnc':
        message = 'Could not create a console of requested type.'
        raise ServiceUnavailable(message)

    # Let vncauthproxy decide on the source port.
    # The alternative: static allocation, e.g.
    # sport = console_data['port'] - 1000
    sport = 0
    daddr = console_data['host']
    dport = console_data['port']
    password = random_password()

    try:
        if settings.TEST:
            fwd = {'source_port': 1234, 'status': 'OK'}
        else:
            fwd = request_vnc_forwarding(sport, daddr, dport, password)
    except Exception:
        raise ServiceUnavailable('Could not allocate VNC console port.')

    if fwd['status'] != "OK":
        raise ServiceUnavailable('Could not allocate VNC console.')

    console = {
        'type': 'vnc',
        'host': getfqdn(),
        'port': fwd['source_port'],
        'password': password}

    if request.serialization == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('console.xml', {'console': console})
    else:
        mimetype = 'application/json'
        data = json.dumps({'console': console})

    return HttpResponse(data, mimetype=mimetype, status=200)

@server_action('firewallProfile')
def set_firewall_profile(request, vm, args):
    # Normal Response Code: 200
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       buildInProgress (409),
    #                       overLimit (413)
    
    profile = args.get('profile', '')
    if profile not in [x[0] for x in NetworkInterface.FIREWALL_PROFILES]:
        raise BadRequest("Unsupported firewall profile")
    backend.set_firewall_profile(vm, profile)
    return HttpResponse(status=202)


@network_action('add')
def add(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    server_id = args.get('serverRef', None)
    if not server_id:
        raise BadRequest('Malformed Request.')
    vm = get_vm(server_id, request.user)
    backend.connect_to_network(vm, net)
    vm.save()
    net.save()
    return HttpResponse(status=202)

@network_action('remove')
def remove(request, net, args):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    server_id = args.get('serverRef', None)
    if not server_id:
        raise BadRequest('Malformed Request.')
    vm = get_vm(server_id, request.user)
    backend.disconnect_from_network(vm, net)
    vm.save()
    net.save()
    return HttpResponse(status=202)
