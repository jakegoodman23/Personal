from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_bootstrap import Bootstrap
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length

import os
import datetime
import pandas as pd

abspath = os.path.abspath(__file__)
dirname = os.path.dirname(abspath)
os.chdir(dirname)

app = Flask(__name__)

app.config['SECRET_KEY'] = '505cfcf30694ea490f71cab51b3500effceeb54c9180b38817243fae7bba03c9'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///staffing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


db = SQLAlchemy(app)

##CREATE TABLE IN DB
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    role = db.Column(db.String(100))
    location = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone_num = db.Column(db.String(100))
    availability = db.Column(db.String(100))
    can_float = db.Column(db.String(100))
    password = db.Column(db.String(100))
    shifts_worked = db.Column(db.Integer)


class Shift(db.Model):
    shift_id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100))
    role = db.Column(db.String(100))
    area = db.Column(db.String(100))
    date = db.Column(db.Date)
    start_time = db.Column(db.String(100))
    end_time = db.Column(db.String(100))
    added_by_id = db.Column(db.Integer)
    added_by_name = db.Column(db.String)
    picked_up_by_id = db.Column(db.Integer)
    picked_up_by_name = db.String(100)


class LoginForm(FlaskForm):
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField(label="Log In")


class RegisterForm(FlaskForm):
    name = StringField(label='Name', validators=[DataRequired()])
    role = SelectField(label='Role', choices=["Admin", "CRNA", "Medical Assistant", "RN", "Scrub Tech"]
                       , validators=[DataRequired()])
    location = StringField(label='Hospital', validators=[DataRequired()])
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    phone_num = StringField(label='Phone Number', validators=[DataRequired()])
    can_float = SelectField(label='Float to other areas?', choices=["Yes", "No", "N/A"], validators=[DataRequired()])
    availability = SelectField(label='Staff member currently available?', choices=["Yes", "No"]
                               , validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[Length(min=8)])
    submit = SubmitField(label="Register")


class UserForm(FlaskForm):
    name = StringField(label='Name', validators=[DataRequired()])
    role = SelectField(label='Role', choices=["Admin", "CRNA", "Medical Assistant", "RN", "Scrub Tech"]
                       , validators=[DataRequired()])
    location = StringField(label='Hospital', validators=[DataRequired()])
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    phone_num = StringField(label='Phone Number', validators=[DataRequired()])
    can_float = SelectField(label='Float to other areas?', choices=["Yes", "No", "N/A"], validators=[DataRequired()])
    availability = SelectField(label='Staff member currently available?', choices=["Yes", "No"]
                               , validators=[DataRequired()])
    submit = SubmitField(label="Add User")


class ShiftForm(FlaskForm):
    location = StringField(label='Hospital', validators=[DataRequired()])
    role = StringField(label='Role (e.g. RN)', validators=[DataRequired()])
    area = StringField(label='Area (e.g. ICU)', validators=[DataRequired()])
    date = DateField(label='Shift Date (format: yyyy-mm-dd)', validators=[DataRequired()])
    start_time = StringField(label='Start Time (e.g. 8am)', validators=[DataRequired()])
    end_time = StringField(label='End Time (e.g. 5pm)', validators=[DataRequired()])
    submit = SubmitField(label="Add Shift")


# Line below only required once, when creating DB.
db.create_all()


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if request.method == "POST":
        email = login_form.email.data
        password = login_form.password.data

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # Email exists and password correct
        else:
            login_user(user)
            return redirect(url_for('staff'))

    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    registration_form = RegisterForm()
    if request.method == "POST":
        if User.query.filter_by(email=registration_form.email.data).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            registration_form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            name=registration_form.name.data,
            role=registration_form.role.data,
            location=registration_form.location.data,
            email=registration_form.email.data,
            phone_num=registration_form.phone_num.data,
            availability=registration_form.availability.data,
            can_float=registration_form.can_float.data,
            password=hash_and_salted_password
        )

        db.session.add(new_user)
        db.session.commit()

        if new_user.role == "Admin":
            return render_template("batch_files.html", user=new_user, logged_in=True)
        else:
            return render_template("login.html", logged_in=True)

    return render_template("register.html", form=registration_form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template("index.html")


@app.route('/downloadstaff')
@login_required
def download_staff():
    return send_from_directory('static', filename="files/staff_roster_template.xlsx")


@app.route('/downloadshifts')
@login_required
def download_shifts():
    return send_from_directory('static', filename="files/shifts_template.xlsx")

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == "POST":
        staff_list = pd.read_excel('example_upload.xlsx')
        for index, row in staff_list.iterrows():
            new_user = User(
                name=row['name'],
                role=row['role'],
                email=row['email'],
                phone_num=row['phone_num'],
                can_float=row['can_float'],
                availability=row['availability'],
                password="password"
            )
            db.session.add(new_user)
            db.session.commit()
        return redirect(url_for('staff'))

    return render_template('batch_files.html', logged_in=True)

@app.route('/shift_upload', methods=['GET', 'POST'])
def shift_upload():
    if request.method == "POST":
        shift_list = pd.read_excel('shift_upload.xlsx')
        cur_user_name = User.query.get(current_user.id).name

        for index, row in shift_list.iterrows():
            new_shift = Shift(
                location=row['location'],
                role=row['role'],
                area=row['area'],
                date=row['date'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                added_by_id=current_user.id,
                added_by_name=cur_user_name
            )
            db.session.add(new_shift)
            db.session.commit()
        return redirect(url_for('shift'))

    return render_template('batch_files.html', logged_in=True)


@app.route('/staff', methods=['GET', 'POST'])
@login_required
def staff():
    all_staff = db.session.query(User).all()
    return render_template('staff.html', staff=all_staff, logged_in=True, user=current_user)


@app.route('/shift', methods=['GET', 'POST'])
@login_required
def shift():
    all_shifts = db.session.query(Shift).all()
    return render_template('shifts.html', shifts=all_shifts, logged_in=True, user=current_user)

@app.route('/addshift', methods=['GET', 'POST'])
@login_required
def add_shift():
    shift_form = ShiftForm()
    cur_user_name = User.query.get(current_user.id).name
    if request.method == "POST":
        new_shift = Shift(
            location=shift_form.location.data,
            role=shift_form.role.data,
            area=shift_form.area.data,
            date=shift_form.date.data,
            start_time=shift_form.start_time.data,
            end_time=shift_form.end_time.data,
            added_by_id=current_user.id,
            added_by_name = cur_user_name
        )

        db.session.add(new_shift)
        db.session.commit()

        return redirect(url_for('shift'))

    return render_template("add_shift.html", form=shift_form, logged_in=True, current_user=current_user)


@app.route('/adduser', methods=['GET', 'POST'])
@login_required
def add_user():
    user_form = UserForm()
    cur_user_name = User.query.get(current_user.id).name
    if request.method == "POST":
        new_user = User(
            name=user_form.name.data,
            role=user_form.role.data,
            location=user_form.location.data,
            email=user_form.email.data,
            phone_num=user_form.phone_num.data,
            availability=user_form.availability.data,
            can_float=user_form.can_float.data,
            password="password"
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('staff'))

    return render_template("add_user.html", form=user_form, logged_in=True, current_user=current_user)

if __name__ == '__main__':
    app.run(debug=True)

