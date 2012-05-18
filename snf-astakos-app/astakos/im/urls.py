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

from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.views import password_change

from astakos.im.forms import ExtendedPasswordResetForm, LoginForm
from astakos.im.settings import IM_MODULES, INVITATIONS_ENABLED, EMAILCHANGE_ENABLED
from astakos.im.views import signed_terms_required

urlpatterns = patterns('astakos.im.views',
    url(r'^$', 'index', {}, name='index'),
    url(r'^login/?$', 'index', {}, name='login'),
    url(r'^profile/?$', 'edit_profile'),
    url(r'^feedback/?$', 'feedback'),
    url(r'^signup/?$', 'signup', {'on_success':'im/login.html', 'extra_context':{'login_form':LoginForm()}}),
    url(r'^logout/?$', 'logout', {'template':'im/login.html', 'extra_context':{'login_form':LoginForm()}}),
    url(r'^activate/?$', 'activate'),
    url(r'^approval_terms/?$', 'approval_terms', {}, name='latest_terms'),
    url(r'^approval_terms/(?P<term_id>\d+)/?$', 'approval_terms'),
    url(r'^password/?$', 'change_password', {}, name='password_change'),
)

if EMAILCHANGE_ENABLED:
    urlpatterns += patterns('astakos.im.views',
        url(r'^email_change/?$', 'change_email', {}, name='email_change'),
        url(r'^email_change/confirm/(?P<activation_key>\w+)/', 'change_email', {},
            name='email_change_confirm')
)
    
urlpatterns += patterns('astakos.im.target',
    url(r'^login/redirect/?$', 'redirect.login')
)

if 'local' in IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        url(r'^local/?$', 'local.login')
    )
    urlpatterns += patterns('django.contrib.auth.views',
        url(r'^local/password_reset/?$', 'password_reset',
         {'email_template_name':'registration/password_email.txt',
          'password_reset_form':ExtendedPasswordResetForm}),
        url(r'^local/password_reset_done/?$', 'password_reset_done'),
        url(r'^local/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$',
         'password_reset_confirm'),
        url(r'^local/password/reset/complete/?$', 'password_reset_complete'),
        url(r'^password_change/?$', 'password_change', {'post_change_redirect':'profile'})
    )

if INVITATIONS_ENABLED:
    urlpatterns += patterns('astakos.im.views',
        url(r'^invite/?$', 'invite')
    )

if 'shibboleth' in IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        url(r'^login/shibboleth/?$', 'shibboleth.login')
    )

if 'twitter' in IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        url(r'^login/twitter/?$', 'twitter.login'),
        url(r'^login/twitter/authenticated/?$', 'twitter.authenticated')
    )

urlpatterns += patterns('astakos.im.api',
    url(r'^authenticate/?$', 'authenticate_old'),
    url(r'^authenticate/v2/?$', 'authenticate'),
    url(r'^get_services/?$', 'get_services'),
    url(r'^get_menu/?$', 'get_menu'),
    url(r'^find_userid/?$', 'find_userid'),
    url(r'^find_email/?$', 'find_email'),
)
