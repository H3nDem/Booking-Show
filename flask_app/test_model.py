from flask_app import model
import pytest


def test_add_and_get_user():
    connection = model.connect(":memory:")
    model.create_database(connection)
    model.add_user(connection, 'test1@example.com', 'secret1')
    model.add_user(connection, 'test2@example.com', 'secret2')
    model.add_manager(connection, 'test3@example.com', 'secret3')
    user1 = model.get_user(connection, 'test1@example.com', 'secret1')
    user2 = model.get_user(connection, 'test2@example.com', 'secret2')
    user3 = model.get_user(connection, 'test3@example.com', 'secret3')
    assert user1 == {'id' : 1, 'email' : 'test1@example.com', 'role' : 'USER'}
    assert user2 == {'id' : 2, 'email' : 'test2@example.com', 'role' : 'USER'}
    assert user3 == {'id' : 3, 'email' : 'test3@example.com', 'role' : 'MANAGER'}


def test_get_user_exception():
    connection = model.connect(":memory:")
    model.create_database(connection)
    model.add_user(connection, 'test@example.com', 'secret')
    with pytest.raises(Exception) as exception_info:
        model.get_user(connection, 'test1@example.com', 'secret')
    assert str(exception_info.value) == 'Utilisateur inconnu'
    with pytest.raises(Exception) as exception_info:
        model.get_user(connection, 'test@example.com', 'secret1')
    assert str(exception_info.value) == 'Utilisateur inconnu'
    with pytest.raises(Exception) as exception_info:
        model.get_user(connection, 'test1@example.com', 'secret1')
    assert str(exception_info.value) == 'Utilisateur inconnu'


def test_add_user_email_unique():
    connection = model.connect(":memory:")
    model.create_database(connection)
    model.add_user(connection, 'test1@example.com', 'secret1')
    with pytest.raises(Exception) as exception_info:
        model.add_user(connection, 'test1@example.com', 'secret2')
    assert str(exception_info.value) == 'UNIQUE constraint failed: users.email'


def test_change_password():
    connection = model.connect(":memory:")
    model.create_database(connection)
    model.add_user(connection, 'test@example.com', 'secret1')
    model.change_password(connection, 'test@example.com', 'secret1', 'secret2')
    user = model.get_user(connection, 'test@example.com', 'secret2')
    assert user == {'id' : 1, 'email' : 'test@example.com', 'role' : 'USER'}
    with pytest.raises(Exception) as exception_info:
        model.get_user(connection, 'test@example.com', 'secret1')
    assert str(exception_info.value) == 'Utilisateur inconnu'


def test_change_password_old_password_check():
    connection = model.connect(":memory:")
    model.create_database(connection)
    model.add_user(connection, 'test@example.com', 'secret1')
    with pytest.raises(Exception) as exception_info:
        model.change_password(connection, 'test@example.com', 'secret2', 'secret1')
    assert str(exception_info.value) == 'Utilisateur inconnu'


def test_change_totp():
    connection = model.connect(":memory:")
    model.create_database(connection)
    model.add_user(connection, 'test@example.com', 'secret')
    user = model.get_user(connection, 'test@example.com', 'secret')
    totp = model.get_totp(connection, user['id'])
    assert totp is None
    totp_secret = 'B2EE6NPLCOMFBKNKN4MESU3VJTGNDB2Y'
    model.change_totp(connection, 'test@example.com', totp_secret)
    totp = model.get_totp(connection, user['id'])
    assert totp == totp_secret
    model.change_totp(connection, 'test@example.com', None)
    totp = model.get_totp(connection, user['id'])
    assert totp is None
