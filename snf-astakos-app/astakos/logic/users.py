# Copyright 2012, 2013, 2014 GRNET S.A. All rights reserved.
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

"""Underlying logic for various Astakos operations on users.

Since not all operations are permitted due to the user's state, below follows a
state diagram that shows the necessary user states for the operation to
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
| Operation  | Must be  | Must not be | Result    |
|============|==========|=============|===========|
| verify     |          | Vf          | Vf        |
| accept     | Vf       | Acc & Act   | Acc & Act |
| activate   | Vf, Acc  | Rj, Act     | Act       |
| reject     | Vf       | Acc, Act    | Rj        |
| deactivate |          |             | ~Act      |
|============|==========|=============|===========|

Also, there are a handful of useful functions (check_*) that incorporate the
above logic and can check if an operation can take place."""

from astakos.im import activation_backends
from astakos.im.models import AstakosUser

activation_backend = activation_backends.get_backend()

# Whenever a change in the above logic happens in activations_backends,
# it must be mirrored here.
# TODO: Find a more elegant way

##
# Get_* functions: Return a user list according to the given state


def get_all():
    """Get a list with all the users."""
    return AstakosUser.objects.all()


def get_active():
    """Get list with active users."""
    return AstakosUser.objects.filter(is_active=True)


def get_inactive():
    """Get list with inactive users."""
    return AstakosUser.objects.filter(is_active=False)


def get_accepted():
    """Get list with accepted users."""
    return AstakosUser.objects.filter(moderated=True, is_rejected=False)


def get_rejected():
    """Get list with rejected users."""
    return AstakosUser.objects.filter(is_rejected=True)


def get_verified():
    """Get list with verified users."""
    return AstakosUser.objects.filter(email_verified=True)


def get_unverified():
    """Get list with unverified users."""
    return AstakosUser.objects.filter(email_verified=False)


##
# Check_* functions: Check if an operation can be applied to a user
def check_reject(user):
    """Check if we can reject a user."""
    if user.email_verified and not user.moderated and not user.is_active:
        return True
    else:
        return False


def check_verify(user):
    """Check if we can verify a user's mail."""
    if not user.email_verified:
        return True
    else:
        return False


# FIXME: Shouldn't it be not (user.moderated or user.is_active)?
def check_accept(user):
    """Check if we can verify a user's mail."""
    if user.email_verified and not (user.moderated and user.is_active):
        return True
    else:
        return False


def check_activate(user):
    """Check if we can activate a user."""
    if (user.email_verified and user.moderated and not
            user.is_rejected and not user.is_active):
        return True
    else:
        return False


# This is strange behavior. Shouldn't we at least deactivate non-deactivated
# users?
def check_deactivate(user):
    """Check if we can deactivate a user."""
    return True


##
# Operations: The necessary logic for operation on a user. Uses extensively
# the activation_backends.
def reject(user, reason):
    """Reject a user."""
    res = activation_backend.handle_moderation(
        user, accept=False, reject_reason=reason)
    activation_backend.send_result_notifications(res, user)
    return res


def verify(user):
    """Verify a user's mail."""
    res = activation_backend.handle_verification(user, user.verification_code)
    #activation_backend.send_result_notifications(res, user)
    return res


def accept(user):
    """Accept a verified user."""
    res = activation_backend.handle_moderation(user, accept=True)
    activation_backend.send_result_notifications(res, user)
    return res


def activate(user):
    """Activate an inactive user."""
    res = activation_backend.activate_user(user)
    return res


def deactivate(user, reason=""):
    """Deactivate an active user."""
    res = activation_backend.deactivate_user(user, reason=reason)
    return res
