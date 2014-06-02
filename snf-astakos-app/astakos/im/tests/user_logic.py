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


from django.test import TestCase
from astakos.im.user_logic import (validate_user_action, verify, accept,
                                   activate, deactivate, reject,
                                   send_verification_mail)
from astakos.im.auth import make_local_user
from astakos.im.models import AstakosUser
from snf_django.lib.api import faults
from django.core import mail


class TestUserActions(TestCase):

    """Testing various actions on user."""

    def setUp(self):
        """Common setup method for this test suite."""
        self.user1 = make_local_user("user1@synnefo.org")

    def tearDown(self):
        """Common teardown method for this test suite."""
        AstakosUser.objects.all().delete()

    def test_activation_chain(self):
        """Test activation logic.

        Test the whole path; from creating a user to activating it.
        """
        # Test verification phase
        self.assertTrue(validate_user_action(self.user1, "VERIFY"))
        res = verify(self.user1)
        self.assertFalse(res.is_error())
        # User cannot be verified twice
        self.assertFalse(validate_user_action(self.user1, "VERIFY"))

        # Test moderation/activation phase
        self.assertTrue(validate_user_action(self.user1, "ACCEPT"))
        res = accept(self.user1)
        self.assertFalse(res.is_error())
        # User cannot be accepted twice
        self.assertFalse(validate_user_action(self.user1, "ACCEPT"))
        # User cannot be rejected
        self.assertFalse(validate_user_action(self.user1, "REJECT"))
        # User cannot be reactivated
        self.assertFalse(validate_user_action(self.user1, "ACTIVATE"))

        # Test deactivation/reactivation
        self.assertTrue(validate_user_action(self.user1, "DEACTIVATE"))
        res = deactivate(self.user1)
        self.assertFalse(res.is_error())
        # User can be deactivated many times
        # Not very practical but this is the way that astakos works
        self.assertTrue(validate_user_action(self.user1, "DEACTIVATE"))
        # User cannot be rejected
        self.assertFalse(validate_user_action(self.user1, "REJECT"))
        # User can be reactivated
        self.assertTrue(validate_user_action(self.user1, "ACTIVATE"))
        # Reactivate user
        res = activate(self.user1)
        self.assertFalse(res.is_error())

    def test_rejection(self):
        """Test if rejections are handled properly."""
        # Verify the user
        self.assertTrue(validate_user_action(self.user1, "VERIFY"))
        res = verify(self.user1)

        # Check rejection
        self.assertTrue(validate_user_action(self.user1, "REJECT"))
        res = reject(self.user1, reason="Because")
        self.assertFalse(res.is_error())

        # Check if reason has been registered
        self.assertEqual(self.user1.rejected_reason, "Because")

    def test_exceptions(self):
        """Test if exceptions are raised properly."""
        # For an unverified user, run validate_user_action and check if
        # NotAllowed is raised for accept, activate, reject.
        for action in ("ACCEPT", "ACTIVATE", "REJECT"):
            with self.assertRaises(faults.NotAllowed) as cm:
                validate_user_action(self.user1, action,
                                     fail_with_exception=True)
            self.assertEqual(cm.exception.message,
                             "Action %s is not allowed." % action)

        # Check if BadRequest is raised for a malformed action name.
        with self.assertRaises(faults.BadRequest) as cm:
            validate_user_action(self.user1, "BAD_ACTION",
                                 fail_with_exception=True)
        self.assertEqual(cm.exception.message, "Unknown action: BAD_ACTION.")

        # Check if NotAllowed is raised when applying a wrong action.
        for action in (accept, activate, reject):
            with self.assertRaises(faults.NotAllowed) as cm:
                action(self.user1)

    def test_verification_mail(self):
        """Test if verification mails are sent correctly."""
        # Check if we can send a verification mail to an unverified user
        res = validate_user_action(self.user1, "SEND_VERIFICATION_MAIL")
        self.assertTrue(res)
        send_verification_mail(self.user1)

        # Check if any mail has been sent and if so, check if it has two
        # important properties: the user's realname and his/her verification
        # code
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        if self.user1.realname not in body:
            self.assertTrue(False)
        if self.user1.verification_code not in body:
            self.assertTrue(False)

        # Verify a user and then check again if we can send a verification
        # mail. This time, we should fail.
        res = verify(self.user1)
        self.assertFalse(res.is_error())
        res = validate_user_action(self.user1, "SEND_VERIFICATION_MAIL")
        self.assertFalse(res)
        with self.assertRaises(faults.NotAllowed):
            send_verification_mail(self.user1)
