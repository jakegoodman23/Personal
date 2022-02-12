from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_bootstrap import Bootstrap
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy

from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Email, Length
from dotenv import load_dotenv

import os
import datetime
import pandas as pd
import smtplib


abspath = os.path.abspath(__file__)
dirname = os.path.dirname(abspath)
os.chdir(dirname)

app = Flask(__name__)

app.config['SECRET_KEY'] = '505cfcf30694ea490f71cab51b3500effceeb54c9180b38817243fae7bba03c9'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///staffing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# allow app to use Bootstrap formatting
Bootstrap(app)

# allow app to have default current user characteristics such as is_authenticated status
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# allow SQLAlchemy to be incorporated from a db perspective
db = SQLAlchemy(app)


# user class and db table
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


# shift class and db table
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
    comments = db.Column(db.String(100))
    status = db.Column(db.String(100))


# class to indicate the fields that'll be used on the app's login form
class LoginForm(FlaskForm):
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField(label="Log In")


# class to indicate the fields that'll be used on the app's registration form
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


# class to indicate the fields that'll be used on the app's Add User form
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


# class to indicate the fields that'll be used on the app's Add Shift form
class ShiftForm(FlaskForm):
    location = StringField(label='Hospital', validators=[DataRequired()])
    role = SelectField(label='Role', choices=["RN", "CRNA", "Medical Assistant", "Scrub Tech"]
                       , validators=[DataRequired()])
    area = StringField(label='Area (e.g. ICU)', validators=[DataRequired()])
    date = DateField(label='Shift Date', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = StringField(label='Start Time (e.g. 8am)', validators=[DataRequired()])
    end_time = StringField(label='End Time (e.g. 5pm)', validators=[DataRequired()])
    comments = StringField(label='Comments (competencies, random notes, etc.)')
    submit = SubmitField(label="Add Shift")


# will create database and the tables that are used in the db's model
db.create_all()


@app.route('/')
def home():
    """
    Will take the user back to the home page that allows the user to either log in or register
    """
    return render_template("index.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    """
    Triggered by a user selecting the login button on the home page or on the navigation bar.
    If successfully logged in the user will be "authenticated" and allowed to use all the app's features
    """
    login_form = LoginForm()
    if request.method == "POST":
        email = login_form.email.data
        password = login_form.password.data

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            flash('That email does not exist, please try again.')
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


# registration function
@app.route('/register', methods=["GET", "POST"])
def register():
    """
    Triggered by a user selecting the Register button on the home page or on the navigation bar.
    Currently, registering will add the user to the "Staff List", however that might change to eventually exclude Admin
    users from being included in the "Staff List"
    """
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
        login_user(new_user)
        if new_user.role == "Admin":
            return render_template("batch_files.html", user=new_user, logged_in=True)
        else:
            return redirect(url_for('staff'))

    return render_template("register.html", form=registration_form)


# logout
@app.route('/logout')
@login_required
def logout():
    """
    Will log the user out and un-authenticate the user's session so access to the app's features is no longer allowed
    until the user logs back in
    """
    logout_user()
    return render_template("index.html")


@app.route('/downloadstaff')
@login_required
def download_staff():
    """
    In the batch files page, if the download button is selected for downloading the staff template, the user will
    have the staff_roster_template excel doc downloaded to their computer
    """
    return send_from_directory('static', filename="files/staff_roster_template.xlsx")


@app.route('/downloadshifts')
@login_required
def download_shifts():
    """
    In the batch files page, if the download button is selected for downloading the shifts template, the user will
    have the shifts_template excel doc downloaded to their computer
    """
    return send_from_directory('static', filename="files/shifts_template.xlsx")


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """
    Placeholder function for now to have an initial file uploaded
    TODO: this will be removed and an actual user upload functionality will be implemented
    """
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
    """
    Placeholder function for now to have an initial file uploaded
    TODO: this will be removed and an actual user upload functionality will be implemented
    """
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
    """
    Will query all non-Admin staff and populate the staff list view
    """
    all_staff = db.session.query(User).filter(User.role != 'Admin').order_by(User.name)
    role_list = db.session.query(User.role.distinct().label("roles"))
    roles = [row.roles for row in role_list.all() if row.roles != 'Admin']
    roles.sort()
    location_list = db.session.query(User.location.distinct().label("locations"))
    locations = [row.locations for row in location_list.all()]
    locations.sort()
    return render_template('staff.html', staff=all_staff, roles=roles, locations=locations, logged_in=True, user=current_user)


@app.route('/shift', methods=['GET', 'POST'])
@login_required
def shift():
    """
    Will query all available shifts and populate the available shifts view
    """
    cur_role = User.query.get(current_user.id).role
    cur_date = datetime.date.today()
    available_shifts = db.session.query(Shift)\
        .filter(Shift.picked_up_by_id == None, Shift.date >= cur_date)\
        .filter((Shift.role == cur_role) | (cur_role == 'Admin'))\
        .order_by(Shift.date, Shift.start_time)
    return render_template('shifts.html', shifts=available_shifts, logged_in=True, user=current_user)


@app.route('/addshift', methods=['GET', 'POST'])
@login_required
def add_shift():
    """
    When not received from a "POST" type request, the user will be taken to the Add Shift form. When the user completes
    that form, this function will store the input of the form and populate the shifts view with the data
    """
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
            added_by_name=cur_user_name,
            comments=shift_form.comments.data,
            status='Posted'
        )

        db.session.add(new_shift)
        db.session.commit()

        return redirect(url_for('shift'))

    return render_template("add_shift.html", form=shift_form, logged_in=True, current_user=current_user)


@app.route('/addusershift', methods=['GET', 'POST'])
@login_required
def add_shift_for_user():
    """
    When not received from a "POST" type request, the user will be taken to the Add Shift form. When the user completes
    that form, this function will store the input of the form and populate the shifts view with the data
    """
    shift_form_for_user = ShiftForm()
    cur_user_name = User.query.get(current_user.id).name
    user_id = request.args.get('id')
    user_info = User.query.get(user_id)
    if request.method == "POST":

        new_shift = Shift(
            location=shift_form_for_user.location.data,
            role=shift_form_for_user.role.data,
            area=shift_form_for_user.area.data,
            date=shift_form_for_user.date.data,
            start_time=shift_form_for_user.start_time.data,
            end_time=shift_form_for_user.end_time.data,
            added_by_id=current_user.id,
            added_by_name=cur_user_name,
            picked_up_by_id=user_id,
            comments=shift_form_for_user.comments.data,
            status='Approved'

        )
        db.session.add(new_shift)
        if user_info.shifts_worked is None:
            user_info.shifts_worked = 0
        user_info.shifts_worked = user_info.shifts_worked + 1
        db.session.commit()

        return redirect(url_for('staff'))

    return render_template("add_shift_staff.html", form=shift_form_for_user, logged_in=True, current_user=current_user,
                           user=user_info)


@app.route('/adduser', methods=['GET', 'POST'])
@login_required
def add_user():
    """
    When not received from a "POST" type request, the user will be taken to the Add User form. When the user completes
    that form, this function will store the input of the form and populate the staff list view with the data
    """
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
            password=generate_password_hash(password="password", method='pbkdf2:sha256', salt_length=8)
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('staff'))

    return render_template("add_user.html", form=user_form, logged_in=True, current_user=current_user)


@app.route('/acceptshift', methods=['GET', 'POST'])
@login_required
def accept_shift():
    if request.method == "POST":
        # Update shift record with info about the user accepting
        cur_shift_id = request.form["id"]
        shift_to_update = Shift.query.get(cur_shift_id)
        shift_to_update.picked_up_by_id = current_user.id
        shift_to_update.status = 'Requested'
        user_to_update = User.query.get(current_user.id)
        if user_to_update.shifts_worked is None:
            user_to_update.shifts_worked = 0
        user_to_update.shifts_worked = user_to_update.shifts_worked + 1
        db.session.commit()
        return redirect(url_for('send_shift_email', shift=cur_shift_id))

    shift_id = request.args.get('id')
    cur_shift = Shift.query.get(shift_id)
    return render_template("accept_shift.html", shift=cur_shift, logged_in=True)


@app.route('/removeshift', methods=['GET', 'POST'])
@login_required
def remove_shift():
    if request.method == "POST":
        # Update shift record with info about the shift being removed
        cur_shift_id = request.form["id"]
        shift_to_update = Shift.query.get(cur_shift_id)
        cur_user = User.query.get(current_user.id)
        if cur_user.role == 'Admin' or shift_to_update.picked_up_by_id == current_user.id:
            user_to_update_id = shift_to_update.picked_up_by_id
            shift_to_update.status = 'Posted'
            shift_to_update.picked_up_by_id = None
            user_to_update = User.query.get(user_to_update_id)
            user_to_update.shifts_worked = user_to_update.shifts_worked - 1
            db.session.commit()
            return redirect(url_for('staff'))
        else:
            flash('You do not have permission to remove this shift!')
            return render_template("remove_shift.html", shift=shift_to_update, logged_in=True, permission=False)

    shift_id = request.args.get('id')
    cur_shift = Shift.query.get(shift_id)
    return render_template("remove_shift.html", shift=cur_shift, logged_in=True, permission=True)


@app.route('/approverequest', methods=['GET', 'POST'])
@login_required
def approve_request():
    if request.method == "POST":
        cur_shift_id = request.form["id"]
        shift_to_update = Shift.query.get(cur_shift_id)
        shift_to_update.status = 'Approved'
        db.session.commit()
        return redirect(url_for('pending_requests'))

    shift_id = request.args.get('id')
    cur_shift = Shift.query.get(shift_id)
    print(f"test: {shift_id}")
    return render_template("approve_request.html", shift=cur_shift, logged_in=True)


@app.route('/denyrequest', methods=['GET', 'POST'])
@login_required
def deny_request():
    if request.method == "POST":
        cur_shift_id = request.form["id"]
        shift_to_update = Shift.query.get(cur_shift_id)
        user_to_update = User.query.get(shift_to_update.picked_up_by_id)
        user_to_update.shifts_worked = user_to_update.shifts_worked - 1
        shift_to_update.status = 'Posted'
        shift_to_update.picked_up_by_id = None
        db.session.commit()
        return redirect(url_for('pending_requests'))

    shift_id = request.args.get('id')
    cur_shift = Shift.query.get(shift_id)
    return render_template("deny_request.html", shift=cur_shift, logged_in=True)

@app.route('/pendingrequests', methods=['GET', 'POST'])
@login_required
def pending_requests():
    cur_date = datetime.date.today()
    shift_requests = db.session.query(Shift)\
        .join(User, Shift.picked_up_by_id == User.id)\
        .filter(Shift.status == 'Requested', Shift.date >= cur_date, Shift.added_by_id == current_user.id)\
        .order_by(Shift.date, Shift.start_time).with_entities(Shift.location, Shift.area, Shift.date, Shift.role,\
                                                              Shift.start_time, Shift.end_time, Shift.comments,\
                                                              Shift.shift_id, User.name)
    return render_template('pending_requests.html', shifts=shift_requests, logged_in=True, user=current_user)

@app.route('/userdetails', methods=['GET', 'POST'])
@login_required
def user_details():
    shift_user_id = request.args.get('id')
    user_shift_info = db.session.query(Shift).filter(Shift.picked_up_by_id == shift_user_id).order_by(Shift.date)\
        .order_by(Shift.date, Shift.start_time)
    user_name = User.query.get(shift_user_id).name
    return render_template('user_shifts.html', shifts=user_shift_info, user_name=user_name, logged_in=True)


@app.route('/edituser', methods=['GET', 'POST'])
@login_required
def edit_user():
    if request.method == "POST":
        user_id = request.form["id"]
        user_to_update = User.query.get(user_id)
        user_to_update.name = request.form["name"]
        user_to_update.role = request.form["role"]
        user_to_update.location = request.form["location"]
        user_to_update.email = request.form["email"]
        user_to_update.phone_num = request.form["phone_num"]
        user_to_update.availability = request.form["availability"]
        user_to_update.can_float = request.form["can_float"]
        db.session.commit()
        return redirect(url_for('staff'))
    user_id = request.args.get('id')
    user_info = User.query.get(user_id)
    return render_template('edit_user.html', user=user_info, logged_in=True)


@app.route('/sendemail', methods=['GET', 'POST'])
@login_required
def send_shift_email():
    parent_path = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(parent_path, 'info.env'))
    email_address = os.getenv("EMAIL")
    email_password = os.getenv("EMAIL_PASSWORD")

    shift_id = request.args['shift']
    accepted_shift = Shift.query.get(shift_id)
    added_by_user = accepted_shift.added_by_id
    posted_user = User.query.get(added_by_user)
    added_by_email = posted_user.email

    contents = f"Your posted shift for {accepted_shift.date} at {accepted_shift.location} in the {accepted_shift.area} " \
               f"area has been picked by: " \
               f"{User.query.get(accepted_shift.picked_up_by_id).name}\n" \
               f"Please navigate to the application to approve or deny the {User.query.get(accepted_shift.picked_up_by_id).name}'s request!\n\n" \
                "From,\nYour trusty pals at iQueue"



    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(email_address, email_password)
        connection.sendmail(
            from_addr=email_address,
            to_addrs=[added_by_email, User.query.get(accepted_shift.picked_up_by_id).email],
            msg=f"Subject:Your {accepted_shift.date} shift has been picked up!!\n\n{contents}"
        )

    return redirect(url_for('shift'))


if __name__ == '__main__':
    app.run(debug=True)
