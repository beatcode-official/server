
import os
import subprocess
import sys
from pprint import pprint

# fmt: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core.config import settings
from tests.integration.functions import *

# fmt: on

# Important: Make sure server is in test mode.
assert settings.TESTING, "Server is not in testing mode"
# Clear database before hand with "python -m db.init --droptest"
subprocess.run(
    ["python", "-m", "db.init", "--droptest"],
    stdout=subprocess.DEVNULL
)

# Global Variables
SKIP = [
    2, 3, 4, 6, 7, 8, 9, 10
]
print(f"Skipping tests: {SKIP}")

# 1. Register a new user
if 1 not in SKIP:
    print("Running test 1: Register a new user", end=" ", flush=True)
    user1 = register_user("jdoe", "jdoe@email.com", "password", "John Doe")

    assert user1["username"] == "jdoe"
    assert user1["email"] == "jdoe@email.com"
    assert user1["display_name"] == "John Doe"
    assert user1["is_verified"] == False
    print("✅")

# 2. Register another user with same username or password
if 2 not in SKIP:
    print("Running test 2: Register another user with same username or password", end=" ", flush=True)
    broken_user1 = register_user("jdoe", "john@email.com", "password", "John Doe")
    assert broken_user1["detail"] == "Username already exists"
    broken_user1 = register_user("john", "jdoe@email.com", "password", "John Doe")
    assert broken_user1["detail"] == "Email already registered"
    broken_user1 = register_user("jdoe", "jdoe@email.com", "password", "John Doe")
    assert broken_user1["detail"] == "Username already exists"
    print("✅")

# 3. Login before verifying
if 3 not in SKIP:
    print("Running test 3: Login before verifying", end=" ", flush=True)
    user1 = login_user("jdoe", "password")
    assert user1["detail"] == "Email not verified"
    print("✅")

# 4. Login with wrong details
if 4 not in SKIP:
    print("Running test 4: Login with wrong details", end=" ", flush=True)
    user1 = login_user("jdoe", "passworddd")
    assert user1["detail"] == "Incorrect login credentials"
    print("✅")

# 5. Verify email and login
if 5 not in SKIP:
    print("Running test 5: Verify email and login", end=" ", flush=True)
    print(verify_email("test_email_token"))
    user1 = login_user("jdoe", "password")

    assert "access_token" in user1
    assert "refresh_token" in user1

    user1_access, user1_refresh = user1["access_token"], user1["refresh_token"]
    print("✅")

# 6. Get, update, and delete user info
if 6 not in SKIP:
    print("Running test 6: Get, update, and delete user info", end=" ", flush=True)
    user1 = get_user(user1_access)
    assert user1["username"] == "jdoe"
    assert user1["email"] == "jdoe@email.com"
    assert user1["display_name"] == "John Doe"
    assert user1["is_verified"] == True

    user1 = update_user(user1_access, {"display_name": "John Doe Jr."})
    assert user1["username"] == "jdoe"
    assert user1["email"] == "jdoe@email.com"
    assert user1["display_name"] == "John Doe Jr."
    assert user1["is_verified"] == True

    delete_user(user1_access)
    user1 = get_user(user1_access)
    assert user1["detail"] == "Could not validate credentials"
    print("✅")

# 7. Forgot and reset password
if 7 not in SKIP:
    print("Running test 7: Forgot and reset password", end=" ", flush=True)
    register_user("janedoe", "janedoe@email.com", "old_password", "Jane Doe")
    verify_email("test_email_token")
    user2 = login_user("janedoe", "old_password")
    assert "access_token" in user2
    assert "refresh_token" in user2
    old_access_token, old_refresh_token = user2["access_token"], user2["refresh_token"]

    forgot_password("janedoe@email.com")
    reset_password("test_email_token", "new_password")
    reset_password("test_email_token", "new_new_password")  # Should fail
    user2 = login_user("janedoe", "old_password")
    assert user2["detail"] == "Incorrect login credentials"
    user2 = login_user("janedoe", "new_new_password")
    assert user2["detail"] == "Incorrect login credentials"

    user2 = login_user("janedoe", "new_password")
    assert "access_token" in user2
    assert "refresh_token" in user2
    new_access_token, new_refresh_token = user2["access_token"], user2["refresh_token"]

    user2 = get_user(old_access_token)
    assert user2["detail"] == "Could not validate credentials"
    user2 = refresh_token(old_refresh_token)
    assert user2["detail"] == "Invalid or expired refresh token"
    user2 = get_user(new_access_token)
    assert user2["username"] == "janedoe"
    user2 = refresh_token(new_refresh_token)
    assert "access_token" in user2
    assert "refresh_token" in user2
    print("✅")

# 8. Refreshing tokens
if 8 not in SKIP:
    print("Running test 8: Refreshing tokens", end=" ", flush=True)
    register_user("lorem", "lorem@email.com", "ipsumpassword", "Lorem Ipsum")
    verify_email("test_email_token")
    user3 = login_user("lorem", "ipsumpassword")
    assert "access_token" in user3
    assert "refresh_token" in user3
    old_access_token, old_refresh_token = user3["access_token"], user3["refresh_token"]

    user3 = refresh_token(old_refresh_token)
    assert "access_token" in user3
    assert "refresh_token" in user3
    new_access_token, new_refresh_token = user3["access_token"], user3["refresh_token"]

    user3 = refresh_token(old_refresh_token)
    assert user3["detail"] == "Invalid or expired refresh token"

    user3 = get_user(new_access_token)
    assert user3["username"] == "lorem"
    user3 = refresh_token(new_refresh_token)
    assert "access_token" in user3
    assert "refresh_token" in user3
    print("✅")

# 9. Log out
if 9 not in SKIP:
    print("Running test 9: Log out", end=" ", flush=True)
    register_user("ipsum", "ipsum@email.com", "lorempassword", "Ipsum Lorem")
    verify_email("test_email_token")
    user4 = login_user("ipsum", "lorempassword")
    user4_access, user4_refresh = user4["access_token"], user4["refresh_token"]

    logout_user(user4_access, user4_refresh)
    user4 = refresh_token(user4_refresh)
    assert user4["detail"] == "Invalid or expired refresh token"
    print("✅")

# 10. Checking validity of access and refresh tokens after password change, user delete, logout
if 10 not in SKIP:
    print("Running test 10: Checking validity of access and refresh tokens after password change, user delete, logout", end=" ", flush=True)
    register_user("user5", "user5@email.com", "password", "User Five")
    verify_email("test_email_token")
    user5 = login_user("user5", "password")
    user5_access, user5_refresh = user5["access_token"], user5["refresh_token"]

    forgot_password("user5@email.com")
    reset_password("test_email_token", "new_password")
    user5 = get_user(user5_access)
    assert user5["detail"] == "Could not validate credentials"
    user5 = refresh_token(user5_refresh)
    assert user5["detail"] == "Invalid or expired refresh token"

    user5 = login_user("user5", "new_password")
    user5_access, user5_refresh = user5["access_token"], user5["refresh_token"]
    logout_user(user5_access, user5_refresh)
    user5 = refresh_token(user5_refresh)
    assert user5["detail"] == "Invalid or expired refresh token"

    user5 = login_user("user5", "new_password")
    user5_access, user5_refresh = user5["access_token"], user5["refresh_token"]
    delete_user(user5_access)
    user5 = get_user(user5_access)
    assert user5["detail"] == "Could not validate credentials"
    user5 = refresh_token(user5_refresh)
    assert user5["detail"] == "Invalid or expired refresh token"
    print("✅")

# Passed!
print("✅ All tests passed!")
