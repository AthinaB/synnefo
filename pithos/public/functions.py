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

import logging

from django.http import HttpResponse

from pithos.api.faults import (Fault, BadRequest, ItemNotFound)
from pithos.api.util import (put_object_headers, update_manifest_meta,
    validate_modification_preconditions, validate_matching_preconditions,
    object_data_response, api_method)


logger = logging.getLogger(__name__)


def object_demux(request, v_account, v_container, v_object):
    if request.method == 'HEAD':
        return object_meta(request, v_account, v_container, v_object)
    elif request.method == 'GET':
        return object_read(request, v_account, v_container, v_object)
    else:
        return method_not_allowed(request)

@api_method('HEAD', user_required=False)
def object_meta(request, v_account, v_container, v_object):
    # Normal Response Codes: 204
    # Error Response Codes: serviceUnavailable (503),
    #                       itemNotFound (404),
    #                       badRequest (400)
    
    try:
        meta = request.backend.get_object_meta(request.user_uniq, v_account,
                                                v_container, v_object)
        public = request.backend.get_object_public(request.user_uniq, v_account,
                                                    v_container, v_object)
    except:
        raise ItemNotFound('Object does not exist')
    
    if not public:
        raise ItemNotFound('Object does not exist')
    update_manifest_meta(request, v_account, meta)
    
    response = HttpResponse(status=200)
    put_object_headers(response, meta, True)
    return response

@api_method('GET', user_required=False)
def object_read(request, v_account, v_container, v_object):
    # Normal Response Codes: 200, 206
    # Error Response Codes: serviceUnavailable (503),
    #                       rangeNotSatisfiable (416),
    #                       preconditionFailed (412),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       notModified (304)
    
    try:
        meta = request.backend.get_object_meta(request.user_uniq, v_account,
                                                v_container, v_object)
        public = request.backend.get_object_public(request.user_uniq, v_account,
                                                    v_container, v_object)
    except:
        raise ItemNotFound('Object does not exist')
    
    if not public:
        raise ItemNotFound('Object does not exist')
    update_manifest_meta(request, v_account, meta)
    
    # Evaluate conditions.
    validate_modification_preconditions(request, meta)
    try:
        validate_matching_preconditions(request, meta)
    except NotModified:
        response = HttpResponse(status=304)
        response['ETag'] = meta['ETag']
        return response
    
    sizes = []
    hashmaps = []
    if 'X-Object-Manifest' in meta:
        try:
            src_container, src_name = split_container_object_string('/' + meta['X-Object-Manifest'])
            objects = request.backend.list_objects(request.user_uniq, v_account,
                                src_container, prefix=src_name, virtual=False)
        except:
            raise ItemNotFound('Object does not exist')
        
        try:
            for x in objects:
                s, h = request.backend.get_object_hashmap(request.user_uniq,
                                        v_account, src_container, x[0], x[1])
                sizes.append(s)
                hashmaps.append(h)
        except:
            raise ItemNotFound('Object does not exist')
    else:
        try:
            s, h = request.backend.get_object_hashmap(request.user_uniq, v_account,
                                                        v_container, v_object)
            sizes.append(s)
            hashmaps.append(h)
        except:
            raise ItemNotFound('Object does not exist')
    
    return object_data_response(request, sizes, hashmaps, meta, True)

@api_method(user_required=False)
def method_not_allowed(request, **v_args):
    raise ItemNotFound('Object does not exist')
