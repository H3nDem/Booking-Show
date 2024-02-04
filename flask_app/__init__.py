import datetime
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, session, url_for
from jinja2 import StrictUndefined
from flask_app import model
from flask_session import Session
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import BooleanField, DateField, IntegerField, SelectField, StringField, PasswordField, EmailField, TextAreaField, TimeField, validators
import pyotp
from flask_qrcode import QRcode

app = Flask(__name__)
app.config['WTF_CSRF_ENABLED'] = True
app.jinja_env.undefined = StrictUndefined
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
CSRFProtect(app)
QRcode(app)

from flask_talisman import Talisman
Talisman(app, content_security_policy={
  'default-src' : '\'none\'',
  'style-src': [ 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/css/bootstrap.min.css' ],
  'img-src' : ['\'self\'', 'data:'],
  'script-src' : '\'none\''
})

def login_required(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    if not 'user' in session:
      return redirect(url_for('login'))
    return func(*args, **kwargs)
  return wrapper

def role_required(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    if session['user']['role'] != "MANAGER":
      print(session['user']['role'])
      return redirect(url_for('home'))
    return func(*args, **kwargs)
  return wrapper


@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


class LoginForm(FlaskForm):
  email = EmailField('email', validators=[validators.DataRequired()])
  password = PasswordField('password', validators=[validators.DataRequired()])
  totp = StringField('totp')

@app.route('/login', methods=['GET', 'POST'])
def login():
  form = LoginForm()
  if form.validate_on_submit():
    try:
      connection = model.connect()
      user = model.get_user(connection, form.email.data, form.password.data)
      totp = model.get_totp(connection, user['id'])
      if totp is not None and not pyotp.TOTP(totp).verify(form.totp.data):
          raise Exception('Double authentification invalide')
      session['user'] = user
      return redirect('/')
    except Exception as exception:
      app.log_exception(exception)
  return render_template('login.html', form=form)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
  session.pop('user')
  return redirect('/')


class ChangePasswordForm(FlaskForm):
    oldPassword = PasswordField('oldPassword', [validators.DataRequired()])
    password = PasswordField('password', [
        validators.DataRequired(),
        validators.EqualTo('confirmPassword', 
                           message='Les mots de passe doivent correspondre')
    ])
    confirmPassword = PasswordField('confirmPassword', [validators.DataRequired()])
    totpEnabled = BooleanField('totpEnabled')


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
  email = session['user']['email']
  form = ChangePasswordForm()
  if form.validate_on_submit():
    try:
      connection = model.connect()
      totp_secret = session['totp_secret'] if form.totpEnabled.data else None
      model.change_password(connection, 
                            email, 
                            form.oldPassword.data,
                            form.password.data)
      model.change_totp(connection, email, totp_secret)
      return redirect('/')
    except Exception as exception:
      app.log_exception(exception)
  totp_secret = pyotp.random_base32()
  totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=email, issuer_name='SoccerApp')
  session['totp_secret'] = totp_secret
  return render_template('change_password.html', form=form, totp_uri=totp_uri)


class CreateUserForm(FlaskForm):
    email = EmailField('email', validators=[validators.DataRequired()])
    password = PasswordField('password', [
        validators.DataRequired(),
        validators.EqualTo('confirmPassword', 
                           message='Les mots de passe doivent correspondre')
    ])
    confirmPassword = PasswordField('confirmPassword', [validators.DataRequired()])


@app.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
  form = CreateUserForm()
  if form.validate_on_submit():
    try:
      connection = model.connect()
      model.add_user(connection, form.email.data, form.password.data)
      return redirect('/')
    except Exception as exception:
      app.log_exception(exception)
  return render_template('create_user.html', form=form)



@app.route('/theaters', methods=['GET'])
@login_required
@role_required
def theaters():
    connection = model.connect()
    theaters = model.get_theaters(connection)
    return render_template('theaters.html', theaters=theaters)


@app.route('/theater/<int:theater_id>', methods=['GET'])
@login_required
@role_required
def theater(theater_id):
    connection = model.connect()
    theater = model.get_theater(connection, theater_id)
    shows = model.get_shows_with_theater(connection, theater_id)
    return render_template('theater.html', theater=theater, shows=shows)



@app.route('/shows', methods=['GET'])
@login_required
def shows():
    connection = model.connect()
    shows = model.get_shows_with_theater(connection)
    show_ids=[]
    for i in model.get_booking(connection, session['user']['id']):
      show_ids.append(i['show_id'])
    nb_specs = {}
    available = {}
    for i in shows:
      nb_specs[i['show_id']] = model.count_spectators(connection, i['show_id'])
      available[i['show_id']] = i['capacity'] - nb_specs[i['show_id']]
    return render_template('shows.html', shows=shows, nb_specs=nb_specs, a=available, ids=show_ids)



@app.route('/show/<int:show_id>', methods=['GET'])
@login_required
def show(show_id):
    connection = model.connect()
    nb_spec = model.count_spectators(connection, show_id)
    spectators = model.get_spectators_with_user_infos(connection, show_id)
    show = model.get_show_with_theater(connection, show_id)
    show_ids=[]
    for i in model.get_booking(connection, session['user']['id']):
      show_ids.append(i['show_id'])
    available = show['capacity'] - nb_spec
    return render_template('show.html', show=show, spectators=spectators, nb_spec=nb_spec, a=available, ids=show_ids)
    

@app.route('/booking/<int:show_id>/<int:user_id>', methods=['GET'])
@login_required
def book(show_id, user_id):
    try:
      connection = model.connect()
      model.book_show(connection, show_id, user_id)
      return redirect(url_for('shows'))
    except Exception as exception:
      app.log_exception(exception)
    return redirect('/')


class TheaterForm(FlaskForm):
  theater_name = StringField('theater_name', validators=[validators.DataRequired(), validators.Length(min=3)])
  capacity = IntegerField('capacity', validators=[validators.InputRequired(),validators.NumberRange(min=0)])


@app.route('/theater/create', methods=['GET', 'POST'])
@login_required
@role_required
def theater_create():
  form = TheaterForm()
  connection = model.connect()
  if form.validate_on_submit():
    try:
      model.add_theater(connection, form.theater_name.data, form.capacity.data)
      return redirect('/')
    except Exception as exception:
      app.log_exception(exception)
  return render_template('theater_create.html', form=form)




class ShowForm(FlaskForm):
  show_name = StringField('show_name', validators=[validators.DataRequired(), validators.Length(min=3)])
  theater = SelectField('theater', validators=[validators.DataRequired()])
  date = DateField('date', validators=[validators.DataRequired()])
  time = TimeField('time', validators=[validators.DataRequired()])
  description = TextAreaField('description', validators=[validators.DataRequired()])


@app.route('/show/create', methods=['GET', 'POST'])
@login_required
@role_required
def show_create():
  form = ShowForm()
  connection = model.connect()
  theaters = model.get_theaters(connection)
  choices = []
  for t in theaters:
     choice = (t['id'], t['name'])
     choices.append(choice)
  form.theater.choices = choices
  if form.validate_on_submit():
    try:
      date = datetime.datetime.combine(form.date.data, form.time.data)
      model.add_show(connection, form.show_name.data, form.theater.data[0], date, form.description.data)
      return redirect('/')
    except Exception as exception:
      app.log_exception(exception)
  return render_template('show_create.html', form=form)


@app.route('/bookings/<int:user_id>', methods=['GET', 'POST'])
@login_required
def my_bookings(user_id):
  connection = model.connect()
  bookings = model.get_booking_detailed(connection, user_id)
  return render_template('bookings.html', bookings=bookings)


@app.route('/booking/<int:booking_id>/delete/', methods=['GET', 'POST'])
@login_required
def cancel_booking(booking_id):
  connection = model.connect()
  model.cancel_booking(connection, booking_id)
  return redirect(url_for('my_bookings', user_id=session['user']['id']))


@app.route('/show/<int:show_id>/delete/', methods=['GET', 'POST'])
@login_required
def delete_show(show_id):
  connection = model.connect()
  model.delete_show(connection, show_id)
  return redirect(url_for('shows'))

