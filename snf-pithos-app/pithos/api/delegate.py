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

from urlparse import urlparse
import urllib
import urllib2

from django.http import HttpResponseNotFound, HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt

from pithos.api.settings import AUTHENTICATION_URL, AUTHENTICATION_USERS, SERVICE_TOKEN


logger = logging.getLogger(__name__)

def delegate_to_login_service(request):
    url = AUTHENTICATION_URL
    users = AUTHENTICATION_USERS
    if users or not url:
        return HttpResponseNotFound()
    
    p = urlparse(url)
    if request.is_secure():
        proto = 'https://'
    else:
        proto = 'http://'
    params = dict([(k, v) for k, v in request.GET.items()])
    uri = proto + p.netloc + '/login?' + urlencode(params)
    return HttpResponseRedirect(uri)

@csrf_exempt
def delegate_to_feedback_service(request):
    url = AUTHENTICATION_URL
    users = AUTHENTICATION_USERS
    if users or not url:
        return HttpResponseNotFound()
    
    p = urlparse(url)
    if request.is_secure():
        proto = 'https://'
    else:
        proto = 'http://'
    
    uri = proto + p.netloc + '/im/service/api/v2.0/feedback'
    headers = { 'X-Auth-Token' : SERVICE_TOKEN }
    headers = {}
    values = dict([(k, v) for k, v in request.POST.items()])
    data = urllib.urlencode(values)
    req = urllib2.Request(uri, data, headers)
    try:
        urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        return HttpResponse(status=e.code)
    return HttpResponse()