# Copyright (C) 2010-2015 GRNET S.A.
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
#

import json

from urllib import unquote

from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template
from django.conf import settings
from synnefo_branding.utils import get_branding_dict

from synnefo_ui import ui_settings


def app(request):
    app_settings = {
        'branding': get_branding_dict(),
        'token': ui_settings.AUTH_METHOD,
        'auth_url': ui_settings.AUTH_URL
    }

    if ui_settings.ASTAKOS_ACCOUNT_PROXY_PATH:
        app_settings['proxy'] = {
            'astakosAccount': ui_settings.ASTAKOS_ACCOUNT_PROXY_PATH
        }

    context = {
        'app_settings': json.dumps(app_settings),
        'UI_MEDIA_URL': ui_settings.UI_MEDIA_URL,
        'UI_BASE_URL': ui_settings.BASE_PATH
    }
    return direct_to_template(request, "snf_ui_index.html",
                              extra_context=context)
