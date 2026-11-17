"""Tests for mask.py. Run: python -m unittest discover -s .claude/skills/secret-masker"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mask import MASK, mask_text  # noqa: E402


class NotePasswordTests(unittest.TestCase):
    def check(self, line: str, expected: str, masked: int) -> None:
        counts: dict[str, int] = {}
        self.assertEqual(mask_text(line, counts), expected)
        self.assertEqual(counts.get("password", 0), masked)

    # Lines from samples/uc1_herokuapp_valid_login_rejected.txt
    def test_herokuapp_creds_user_slash_password(self):
        self.check(
            "the-internet herokuapp /login page. valid creds tomsmith / SuperSecretPassword! rejected",
            f"the-internet herokuapp /login page. valid creds tomsmith / {MASK} rejected",
            1,
        )

    def test_herokuapp_pwd_followed_by_prose_is_kept(self):
        line = 'happened from ~10:15 today, worked yesterday. invalid pwd gives "Your password is invalid!" correctly.'
        self.check(line, line, 0)

    def test_herokuapp_set_cookie_still_masked(self):
        self.assertEqual(
            mask_text("Set-Cookie: rack.session=FAKEsess1on123; path=/; HttpOnly"),
            f"Set-Cookie: {MASK}",
        )

    # Lines from samples/uc1_saucedemo_locked_out_login.txt
    def test_saucedemo_user_plus_pwd(self):
        self.check(
            "entered username locked_out_user + pwd secret_sauce, clicked Login",
            f"entered username locked_out_user + pwd {MASK}, clicked Login",
            1,
        )

    def test_saucedemo_same_pwd_without_value_is_kept(self):
        line = "standard_user logs in fine with same pwd. need this acct for checkout regression. tried 3 times."
        self.check(line, line, 0)

    # Other forms
    def test_password_next_word(self):
        self.check("login with password hunter2 fails", f"login with password {MASK} fails", 1)

    def test_password_at_sentence_end(self):
        self.check("used password hunter2.", f"used password {MASK}.", 1)

    def test_prose_after_password_is_kept(self):
        for line in ("forgot password flow", "password reset link", "the password field", "password is wrong"):
            self.check(line, line, 0)

    def test_already_masked_is_not_counted(self):
        self.check(f"pwd {MASK}", f"pwd {MASK}", 0)

    def test_value_does_not_cross_lines(self):
        self.check("enter pwd\nnext line", "enter pwd\nnext line", 0)

    def test_assignment_form_unchanged(self):
        self.assertEqual(mask_text("password=abc123"), f"password={MASK}")

    # Line from samples/attachments/uc1_att_login_screenshot/notes.txt
    def test_password_followed_by_from_is_kept(self):
        line = "used the normal password from the login page. standard_user works."
        self.check(line, line, 0)


class JsonKeyTests(unittest.TestCase):
    """Quoted JSON/HAR keys, as in samples/attachments/uc1_att_api_response_json."""

    def test_json_api_key_masked(self):
        self.assertEqual(
            mask_text('"x-api-key": "pk_live_51abcDEF"'),
            f'"x-api-key": "{MASK}"',
        )

    def test_json_password_and_token_masked(self):
        counts: dict[str, int] = {}
        text = '{"password": "hunter2", "access_token": "abc.def.ghi"}'
        self.assertEqual(
            mask_text(text, counts),
            f'{{"password": "{MASK}", "access_token": "{MASK}"}}',
        )
        self.assertEqual(counts, {"password": 1, "token": 1})

    def test_json_unrelated_keys_kept(self):
        text = '{"status": 500, "message": "NullPointerException"}'
        self.assertEqual(mask_text(text), text)


if __name__ == "__main__":
    unittest.main()
