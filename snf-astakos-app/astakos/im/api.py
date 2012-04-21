# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
import urllib

from functools import wraps
from traceback import format_exc
from time import time, mktime
from urllib import quote
from urlparse import urlparse

from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson as json
from django.core.urlresolvers import reverse

from astakos.im.faults import BadRequest, Unauthorized, InternalServerError, Fault
from astakos.im.models import AstakosUser
from astakos.im.settings import CLOUD_SERVICES, INVITATIONS_ENABLED, COOKIE_NAME
from astakos.im.util import has_signed_terms, epoch

logger = logging.getLogger(__name__)

def render_fault(request, fault):
    if isinstance(fault, InternalServerError) and settings.DEBUG:
        fault.details = format_exc(fault)

    request.serialization = 'text'
    data = fault.message + '\n'
    if fault.details:
        data += '\n' + fault.details
    response = HttpResponse(data, status=fault.code)
    response['Content-Length'] = len(response.content)
    return response

def api_method(http_method=None, token_required=False, perms=[]):
    """Decorator function for views that implement an API method."""
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')
                x_auth_token = request.META.get('HTTP_X_AUTH_TOKEN')
                if token_required:
                    if not x_auth_token:
                        raise Unauthorized('Access denied')
                    try:
                        user = AstakosUser.objects.get(auth_token=x_auth_token)
                        if not user.has_perms(perms):
                            raise Unauthorized('Unauthorized request')
                    except AstakosUser.DoesNotExist, e:
                        raise Unauthorized('Invalid X-Auth-Token')
                    kwargs['user'] = user
                response = func(request, *args, **kwargs)
                return response
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                logger.exception('Unexpected error: %s' % e)
                fault = InternalServerError('Unexpected error')
                return render_fault(request, fault)
        return wrapper
    return decorator

@api_method(http_method='GET', token_required=True)
def authenticate_old(request, user=None):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    if not user:
        raise BadRequest('No user')
    
    # Check if the is active.
    if not user.is_active:
        raise Unauthorized('User inactive')

    # Check if the token has expired.
    if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
        raise Unauthorized('Authentication expired')
    
    if not has_signed_terms(user):
        raise Unauthorized('Pending approval terms')
    
    response = HttpResponse()
    response.status=204
    user_info = {'username':user.username,
                 'uniq':user.email,
                 'auth_token':user.auth_token,
                 'auth_token_created':user.auth_token_created.isoformat(),
                 'auth_token_expires':user.auth_token_expires.isoformat(),
                 'has_credits':user.has_credits,
                 'has_signed_terms':has_signed_terms(user)}
    response.content = json.dumps(user_info)
    response['Content-Type'] = 'application/json; charset=UTF-8'
    response['Content-Length'] = len(response.content)
    return response

@api_method(http_method='GET', token_required=True)
def authenticate(request, user=None):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    if not user:
        raise BadRequest('No user')
    
    # Check if the is active.
    if not user.is_active:
        raise Unauthorized('User inactive')

    # Check if the token has expired.
    if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
        raise Unauthorized('Authentication expired')
    
    if not has_signed_terms(user):
        raise Unauthorized('Pending approval terms')
    
    response = HttpResponse()
    response.status=204
    user_info = {'userid':user.username,
                 'email':[user.email],
                 'name':user.realname,
                 'auth_token':user.auth_token,
                 'auth_token_created':epoch(user.auth_token_created),
                 'auth_token_expires':epoch(user.auth_token_expires),
                 'has_credits':user.has_credits,
                 'is_active':user.is_active,
                 'groups':[g.name for g in user.groups.all()]}
    response.content = json.dumps(user_info)
    response['Content-Type'] = 'application/json; charset=UTF-8'
    response['Content-Length'] = len(response.content)
    return response

@api_method(http_method='GET')
def get_services(request):
    callback = request.GET.get('callback', None)
    data = json.dumps(CLOUD_SERVICES)
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)

@api_method()
def get_menu(request, with_extra_links=False, with_signout=True):
    exclude = []
    index_url = reverse('index')
    absolute = lambda (url): request.build_absolute_uri(url)
    l = [{ 'url': absolute(index_url), 'name': "Sign in"}]
    cookie = urllib.unquote(request.COOKIES.get(COOKIE_NAME, ''))
    email = cookie.partition('|')[0]
    try:
        user = AstakosUser.objects.get(email=email, is_active=True)
    except AstakosUser.DoesNotExist:
        pass
    else:
        l = []
        l.append({ 'url': absolute(reverse('astakos.im.views.index')),
                  'name': user.email})
        l.append({ 'url': absolute(reverse('astakos.im.views.edit_profile')),
                  'name': "My account" })
        if with_extra_links:
            if user.has_usable_password():
                l.append({ 'url': absolute(reverse('password_change')),
                          'name': "Change password" })
            if INVITATIONS_ENABLED:
                l.append({ 'url': absolute(reverse('astakos.im.views.invite')),
                          'name': "Invitations" })
            l.append({ 'url': absolute(reverse('astakos.im.views.feedback')),
                      'name': "Feedback" })
        if with_signout:
            l.append({ 'url': absolute(reverse('astakos.im.views.logout')),
                      'name': "Sign out"})
    
    callback = request.GET.get('callback', None)
    data = json.dumps(tuple(l))
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)

@api_method(http_method='GET', token_required=True, perms=['astakos.im.can_find_userid'])
def find_userid(request):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    email = request.GET.get('email')
    if not email:
        raise BadRequest('Email missing')
    try:
        user = AstakosUser.objects.get(email = email, is_active=True)
    except AstakosUser.DoesNotExist, e:
        raise BadRequest('Invalid email')
    else:
        response = HttpResponse()
        response.status=204
        user_info = {'userid':user.username}
        response.content = json.dumps(user_info)
        response['Content-Type'] = 'application/json; charset=UTF-8'
        response['Content-Length'] = len(response.content)
        return response

@api_method(http_method='GET', token_required=True, perms=['astakos.im.can_find_email'])
def find_email(request):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    userid = request.GET.get('userid')
    if not userid:
        raise BadRequest('Userid missing')
    try:
        user = AstakosUser.objects.get(username = userid)
    except AstakosUser.DoesNotExist, e:
        raise BadRequest('Invalid userid')
    else:
        response = HttpResponse()
        response.status=204
        user_info = {'userid':user.email}
        response.content = json.dumps(user_info)
        response['Content-Type'] = 'application/json; charset=UTF-8'
        response['Content-Length'] = len(response.content)
        return response
