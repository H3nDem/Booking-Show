DROP TABLE IF EXISTS shows;    /* Spectacle */
DROP TABLE IF EXISTS theaters; /* Salle de spectacle */
DROP TABLE IF EXISTS users;    /* Utilisateurs : Clients + gestionnaire */
DROP TABLE IF EXISTS bookings; /* Reservations */

CREATE TABLE shows(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(64) NOT NULL,
  theater_id INTEGER NOT NULL,
  date DATETIME NOT NULL,
  description VARCHAR(2048) NOT NULL,
  
  FOREIGN KEY (theater_id) REFERENCES theaters(id),
  UNIQUE (theater_id, date)
);

CREATE TABLE theaters(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(64) NOT NULL,
  capacity INTEGER NOT NULL,

  UNIQUE (name),
  CHECK (capacity >= 0)
);

CREATE TABLE users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email VARCHAR(128) NOT NULL,
  password_hash VARCHAR(128) NOT NULL,
  role VARCHAR(64),
  totp CHAR(32),

  UNIQUE (email)
);

CREATE TABLE bookings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  show_id INTEGER NOT NULL,
  
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (show_id) REFERENCES shows(id),
  UNIQUE (user_id, show_id)
)
