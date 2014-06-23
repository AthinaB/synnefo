# Copyright 2012 - 2014 GRNET S.A. All rights reserved.
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

"""Url configuration for the admin interface"""

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'synnefo_admin.admin.views',
    url(r'^$', 'home', name='admin-home'),
    url(r'^logout$', 'logout', name='admin-logout'),
    url(r'^charts$', 'charts', name='admin-charts'),
    url(r'^stats$', 'stats', name='admin-stats'),
    url(r'^json/(?P<type>.*)$', 'json_list', name='admin-json'),
    url(r'^actions/(?P<resource>.*)/(?P<op>.*)/(?P<id>.*)$',
        'admin_actions_id', name='admin-actions-id'),
    url(r'^actions/$', 'admin_actions', name='admin-actions'),
    url(r'^(?P<type>.*)/(?P<id>.*)$', 'details', name='admin-details'),
    url(r'^(?P<type>.*)$', 'catalog', name='admin-list'),
)
