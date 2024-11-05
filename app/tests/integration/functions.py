import requests

BASE_URL = "http://localhost:8000/api"
API_MAP = {
    "register": "/users/register",
    "login": "/users/login",
    "verify": "/users/verify-email",
    "user": "/users/me",
    "forgot": "/users/forgot-password",
    "reset": "/users/reset-password",
    "refresh": "/users/refresh",
    "logout": "/users/logout",
}


def register_user(username, email, password, display_name):
    url = f"{BASE_URL}{API_MAP['register']}"
    data = {
        "username": username,
        "email": email,
        "password": password,
        "display_name": display_name
    }

    response = requests.post(url, json=data)
    return response.json()


def login_user(username, password):
    url = f"{BASE_URL}{API_MAP['login']}"
    data = {
        "username": username,
        "password": password
    }

    response = requests.post(url, data=data)
    return response.json()


def verify_email(token):
    url = f"{BASE_URL}{API_MAP['verify']}/{token}"

    response = requests.get(url)
    return response.json()


def get_user(access_token):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    return response.json()


def update_user(access_token, data):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.patch(url, headers=headers, json=data)
    return response.json()


def delete_user(access_token):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.delete(url, headers=headers)


def forgot_password(email):
    url = f"{BASE_URL}{API_MAP['forgot']}"
    data = {
        "email": email
    }

    response = requests.post(url, json=data)
    return response.json()


def reset_password(token, password):
    url = f"{BASE_URL}{API_MAP['reset']}"
    data = {
        "token": token,
        "new_password": password
    }

    response = requests.post(url, json=data)
    return response.json()


def refresh_token(refresh_token):
    url = f"{BASE_URL}{API_MAP['refresh']}"
    data = {
        "refresh_token": refresh_token
    }

    response = requests.post(url, json=data)
    return response.json()


def logout_user(access_token, refresh_token):
    url = f"{BASE_URL}{API_MAP['logout']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    data = {
        "refresh_token": refresh_token
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()
