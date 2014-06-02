# Copyright (C) 2010-2014 GRNET S.A.
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


"""Underlying logic for various Astakos actions on users.

This module includes the necessary logic for various Astakos actions. It
provides a function to check if an action can be applied on an AstakosUser
(`validate_user_action`) as well as all of the actions, decorated by the
aforementioned function.

Since not all actions are permitted due to the user's state, below follows a
state diagram that shows the necessary user states for the action to
succeed. If a state is not mentioned for an operation, then it does not affect
it.

Legend:
    Rj = rejected,
    Acc = accepted,
    Act = activated,
    Vf = verified
    ~ = logical not (negation of state)
    & = logical and (conjuction of states)

|============|==========|=============|===========|
| Action     | Must be  | Must not be | Result    |
|============|==========|=============|===========|
| verify     |          | Vf          | Vf        |
| accept     | Vf       | Acc & Act   | Acc & Act |
| activate   | Vf, Acc  | Rj, Act     | Act       |
| reject     | Vf       | Acc, Act    | Rj        |
| deactivate |          |             | ~Act      |
|============|==========|=============|===========|

"""

import functools

from astakos.im import activation_backends
from astakos.im.models import AstakosUser
from snf_django.lib.api import faults

activation_backend = activation_backends.get_backend()


##
# Check functions
def validate_user_action(user, action, fail_with_exception=False):

    def fail_not_allowed(action, fail_with_exception):
        if fail_with_exception:
            raise faults.NotAllowed("Action %s is not allowed." % action)
        else:
            return False

    def fail_bad_request(action, fail_with_exception):
        if fail_with_exception:
            raise faults.BadRequest("Unknown action: %s." % action)
        else:
            return False

    if action == "VERIFY":
        if not user.email_verified:
            return True
    elif action == "REJECT":
        if user.email_verified and not user.moderated and not user.is_active:
            return True
    elif action == "ACCEPT":
        # FIXME: Shouldn't it be not (user.moderated or user.is_active)?
        if user.email_verified and not (user.moderated and user.is_active):
            return True
    elif action == "ACTIVATE":
        if (user.email_verified and user.moderated and not
                user.is_rejected and not user.is_active):
            return True
    elif action == "DEACTIVATE":
        # FIXME: This is strange behavior. Shouldn't we deactivate only
        # activated users?
        return True
    elif action == "SEND_VERIFICATION_MAIL":
        # FIXME: This is strange behavior. Shouldn't we deactivate only
        # activated users?
        if not user.email_verified:
            return True
    else:
        return fail_bad_request(action, fail_with_exception)

    return fail_not_allowed(action, fail_with_exception)


def user_action(action):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            validate_user_action(user, action, fail_with_exception=True)
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


##
# Actions: The necessary logic for actions on a user. Uses extensively
# the activation_backends.
@user_action("REJECT")
def reject(user, reason):
    """Reject a user."""
    res = activation_backend.handle_moderation(
        user, accept=False, reject_reason=reason)
    activation_backend.send_result_notifications(res, user)
    return res


@user_action("VERIFY")
def verify(user):
    """Verify a user's mail."""
    res = activation_backend.handle_verification(user, user.verification_code)
    #activation_backend.send_result_notifications(res, user)
    return res


@user_action("ACCEPT")
def accept(user):
    """Accept a verified user."""
    res = activation_backend.handle_moderation(user, accept=True)
    activation_backend.send_result_notifications(res, user)
    return res


@user_action("ACTIVATE")
def activate(user):
    """Activate an inactive user."""
    res = activation_backend.activate_user(user)
    return res


@user_action("DEACTIVATE")
def deactivate(user, reason=""):
    """Deactivate an active user."""
    res = activation_backend.deactivate_user(user, reason=reason)
    return res


@user_action("SEND_VERIFICATION_MAIL")
def send_verification_mail(user):
    """Send verification mail to an unverified user."""
    res = activation_backend.send_user_verification_email(user)
    return res
