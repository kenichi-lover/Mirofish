import os
import unittest
from datetime import datetime, timedelta, timezone

import jwt

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-project-123456")

from app.utils.jwt import create_access_token, decode_access_token


class JWTTokenTests(unittest.TestCase):
    def test_create_access_token_includes_custom_claims(self):
        token = create_access_token(
            "user-1",
            extra_claims={"role": "admin", "tenant": "acme"},
        )

        payload = decode_access_token(token)

        self.assertEqual(payload["sub"], "user-1")
        self.assertEqual(payload["role"], "admin")
        self.assertEqual(payload["tenant"], "acme")
        self.assertEqual(payload["type"], "access")
        self.assertIn("jti", payload)

    def test_decode_access_token_rejects_expired_tokens(self):
        expired_payload = {
            "sub": "user-1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "jti": "expired-token",
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_payload,
            os.environ["SECRET_KEY"],
            algorithm="HS256",
        )

        with self.assertRaises(jwt.ExpiredSignatureError):
            decode_access_token(expired_token)


if __name__ == "__main__":
    unittest.main()
