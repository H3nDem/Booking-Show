import sqlite3
import os
from passlib.hash import scrypt


def dictionary_factory(cursor, row):
  dictionary = {}
  for index in range(len(cursor.description)):
    column_name = cursor.description[index][0]
    dictionary[column_name] = row[index]
  return dictionary


def connect(database = "database.sqlite"):
  connection = sqlite3.connect(database)
  connection.set_trace_callback(print)
  connection.execute('PRAGMA foreign_keys = 1')
  connection.row_factory = dictionary_factory
  return connection


def read_build_script():
  path = os.path.join(os.path.dirname(__file__), 'build.sql')
  file = open(path)
  script = file.read()
  file.close()
  return script


def create_database(connection):
  script = read_build_script()
  connection.executescript(script)
  connection.commit()


def fill_database(connection):
  add_user(connection, 'user@example.com', 'secret')
  add_user(connection, 'user2@example.com', 'secret2')
  add_manager(connection, 'user3@example.com', 'secret3')
  add_theater(connection, 'Petite salle', 50)
  add_theater(connection, 'Salle moyenne', 150)
  add_theater(connection, 'Grande salle', 500)
  add_theater(connection, '\"Petite\" salle', 1000000)
  add_show(connection, 'Spectacle 1', 1, '2023-11-30 21:00:00', "Descriptif 1")
  add_show(connection, 'Spectacle 2', 2, '2023-11-30 21:00:00', "Descriptif 2")
  add_show(connection, 'Spectacle 3', 1, '2023-11-30 22:00:00', "Descriptif 3")
  add_show(connection, 'Spectacle 4', 3, '2023-11-30 22:00:00', "Descriptif 4")
  add_show(connection, 'Spectacle \"quelconque\"', 4, '2023-11-30 22:00:00', "Bienvenue dans ce \"banal\" spectacle, avec rien de surprenant...")


def hash_password(password):
  return scrypt.using(salt_size=16).hash(password)


def add_user(connection, email, password):
  sql = '''
    INSERT INTO users(email, password_hash, role) VALUES (:email, :password_hash, :role);
  '''
  password_hash = hash_password(password)
  connection.execute(sql, { 'email' : email, 'password_hash' : password_hash, 'role' : 'USER' })
  connection.commit()


def add_manager(connection, email, password):
  sql = '''
    INSERT INTO users(email, password_hash, role) VALUES (:email, :password_hash, :role);
  '''
  password_hash = hash_password(password)
  connection.execute(sql, {
    'email' : email,
    'password_hash' : password_hash,
    'role' : 'MANAGER'
  })
  connection.commit()


def get_user(connection, email, password):
  sql = '''
    SELECT * FROM users
    WHERE email = :email;
  '''
  cursor = connection.execute(sql, {'email': email})
  users = cursor.fetchall()
  if len(users) == 0:
    raise Exception('Utilisateur inconnu')
  user = users[0]
  if not scrypt.verify(password, user['password_hash']):
    raise Exception('Utilisateur inconnu')
  return {'id' : user['id'], 'email' : user['email'], 'role' : user['role']}


def change_password(connection, email, old_password, new_password):
  get_user(connection, email, old_password)
  sql = '''
    UPDATE users
    SET password_hash = :password_hash
    WHERE email = :email
  '''
  password_hash = hash_password(new_password)
  connection.execute(sql, {
    'email' : email,
    'password_hash' : password_hash
  })
  connection.commit()


def change_totp(connection, email, totp_secret):
  sql = '''
    UPDATE users
    SET totp = :totp_secret
    WHERE email = :email
  '''
  connection.execute(sql, {'email' : email, 'totp_secret': totp_secret})
  connection.commit()


def get_totp(connection, user_id):
  sql = '''
    SELECT totp FROM users
    WHERE id = :user_id
  '''
  cursor = connection.execute(sql, {'user_id' : user_id})
  users = cursor.fetchall()
  if len(users) == 0:
    raise Exception('Utilisateur inconnu')
  user = users[0]
  return user['totp']



'''
Methodes pour les salles de spectacle
'''
def add_theater(connection, name, capacity):
  sql = 'INSERT INTO theaters(name, capacity) VALUES (:name, :capacity)'
  connection.execute(sql, {'name' : name, 'capacity' : capacity})
  connection.commit()

def get_theaters(connection):
  sql = 'SELECT * FROM theaters ORDER BY id;'
  cursor = connection.execute(sql)
  return cursor.fetchall()

def get_theater(connection, theater_id):
  sql = 'SELECT * FROM theaters WHERE id = :id;'
  cursor = connection.execute(sql, {'id' : theater_id})
  theaters = cursor.fetchall()
  if len(theaters) == 0:
    raise Exception('Salle de spectacle inconnue')
  return theaters[0]



'''
Methodes pour les spectacles
'''
def add_show(connection, name, theater_id, date, description):
  sql = 'INSERT INTO shows(name, theater_id, date, description) VALUES (:name, :theater_id, :date, :description)'
  connection.execute(sql, {'name' : name, 'theater_id' : theater_id, 'date' : date, 'description' : description})
  connection.commit()

def get_shows(connection, theater_id=None):
  if theater_id == None :
    sql = 'SELECT * FROM shows ORDER BY id;'
  else:
    sql = 'SELECT * FROM shows WHERE theater_id = :theater_id ORDER BY id;'
  cursor = connection.execute(sql, {'theater_id' : theater_id})
  return cursor.fetchall()

def get_show(connection, show_id):
  sql = 'SELECT * FROM shows WHERE id = :id;'
  cursor = connection.execute(sql, {'id' : show_id})
  shows = cursor.fetchall()
  if len(shows) == 0:
    raise Exception('Spectacle inconnu')
  return shows[0]


'''
Methodes pour les reservations
'''

def get_show_with_theater(connection, show_id):
  sql = '''
    SELECT shows.*, theaters.name AS theater_name, theaters.capacity FROM shows
    JOIN theaters ON shows.theater_id = theaters.id
    WHERE shows.id = :id
  '''
  cursor = connection.execute(sql, {'id' : show_id})
  return cursor.fetchall()[0]



def get_shows_with_theater(connection, theater_id=None):
  if (theater_id == None):
    sql = '''
    SELECT shows.id AS show_id,
           shows.name AS show_name,
           shows.date AS show_date,
           shows.description,
           theaters.id AS theater_id,
           theaters.name AS theater_name,
           theaters.capacity
    FROM shows JOIN theaters ON shows.theater_id = theaters.id
    '''
  else:  
    sql = '''
      SELECT shows.id AS show_id,
            shows.name AS show_name,
            shows.date AS show_date,
            theaters.id AS theater_id,
            theaters.name AS theater_name,
            theaters.capacity 
      FROM shows JOIN theaters ON shows.theater_id = theaters.id
      WHERE theaters.id = :id
    '''
  cursor = connection.execute(sql, {'id' : theater_id})
  return cursor.fetchall()




def count_spectators(connection, show_id):
  sql = 'SELECT COUNT(*) AS spectator FROM bookings WHERE show_id = :show_id'
  cursor = connection.execute(sql, {'show_id' : show_id})
  spectators_count = cursor.fetchall()
  return spectators_count[0]['spectator']


def get_spectators(connection, show_id):
  sql = 'SELECT * FROM bookings WHERE show_id = :show_id'
  cursor = connection.execute(sql, {'show_id' : show_id})
  spectators_count = cursor.fetchall()
  return spectators_count

def get_spectators_with_user_infos(connection, show_id):
  sql = 'SELECT bookings.*, users.email FROM bookings JOIN users ON bookings.user_id = users.id WHERE bookings.show_id = :show_id'
  cursor = connection.execute(sql, {'show_id' : show_id})
  spectators_count = cursor.fetchall()
  return spectators_count




def book_show(connection, show_id, user_id):
  show_infos = get_show_with_theater(connection, show_id)
  spectators_count = count_spectators(connection, show_id)
  if (spectators_count < show_infos['capacity']):
    sql = 'INSERT INTO bookings(user_id, show_id) VALUES (:user_id, :show_id)'
    connection.execute(sql, {'user_id' : user_id, 'show_id' : show_id})
    connection.commit()


def get_booking(connection, user_id):
  sql = 'SELECT * FROM bookings JOIN shows ON bookings.show_id = shows.id WHERE bookings.user_id = :id'
  cursor = connection.execute(sql, {'id' : user_id})
  bookings = cursor.fetchall()
  return bookings

def get_booking_detailed(connection, user_id):
  sql = 'SELECT bookings.*, shows.name AS show_name, shows.date, shows.description, theaters.name AS theater_name FROM bookings JOIN shows JOIN theaters ON bookings.show_id = shows.id AND shows.theater_id = theaters.id WHERE bookings.user_id = :id'
  cursor = connection.execute(sql, {'id' : user_id})
  bookings = cursor.fetchall()
  return bookings

def cancel_booking(connection, booking_id):
  sql = 'DELETE FROM bookings WHERE bookings.id = :id'
  connection.execute(sql, {'id' : booking_id})
  connection.commit()

def delete_show(connection, show_id):
  sql2 = 'DELETE FROM bookings WHERE bookings.show_id = :id'
  sql = 'DELETE FROM shows WHERE id = :id;'
  connection.execute(sql2, {'id' : show_id})
  connection.execute(sql, {'id' : show_id})
  connection.commit()
