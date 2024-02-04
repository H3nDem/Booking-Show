"""
REMARQUE :  Par defaut, 3 utilisateurs sont présents
            CLIENT       "user@example.com" avec le mot de passe "secret"
            CLIENT       "user2@example.com" avec le mot de passe "secret2"
            GESTIONNAIRE "user3@example.com" avec le mot de passe "secret3"
"""

from flask_app import model
connection = model.connect()
model.create_database(connection)
model.fill_database(connection)