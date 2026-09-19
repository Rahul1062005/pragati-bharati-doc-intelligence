import pytest
from fastapi import status

def test_register_user_success(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "newuser@pragatibharati.in",
        "username": "newuser",
        "password": "Password123!"
    })
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["email"] == "newuser@pragatibharati.in"
    assert "id" in data

def test_register_duplicate_email(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "newuser@pragatibharati.in",
        "username": "anotheruser",
        "password": "Password123!"
    })
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in res.json()["detail"]

def test_login_success(client, test_user):
    res = client.post("/api/v1/auth/login/json", json={
        "email": "tester@pragatibharati.in",
        "password": "TestPassword123!"
    })
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_password(client, test_user):
    res = client.post("/api/v1/auth/login/json", json={
        "email": "tester@pragatibharati.in",
        "password": "WrongPassword!"
    })
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_me_profile(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["email"] == "tester@pragatibharati.in"
