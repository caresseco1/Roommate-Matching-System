from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, IntegerField, SelectField,
                     TextAreaField, SubmitField, HiddenField)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo, Regexp, ValidationError


class SignupForm(FlaskForm):
    username = StringField('Full Name', validators=[DataRequired(), Length(2, 100), Regexp(r'^[a-zA-Z\s]+$', message='Username must contain only letters (a-z)')])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(r'(?=.*[A-Z])(?=.*\d)',
               message='Must contain at least one uppercase letter and one digit')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class OTPForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[DataRequired(), Length(6, 6)])
    submit = SubmitField('Verify')


class LookingForForm(FlaskForm):
    looking_for = SelectField('Looking For', choices=[
        ('room', 'Looking for a Room'),
        ('roomate', 'Looking for a Roommate')
    ], validators=[DataRequired()])
    submit = SubmitField('Continue')


class RegistrationForm(FlaskForm):
    # Demographics
    profile_pic = FileField('Profile Picture', validators=[
        Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Images only!')])
    room_price = IntegerField('Room Price (₹/month)', validators=[Optional(), NumberRange(1000, 500000)])
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(16, 70)])
    gender = SelectField('Gender', choices=[
        ('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Non-binary', 'Non-binary')
    ], validators=[DataRequired()])
    occupation = StringField('Occupation', validators=[DataRequired(), Length(2, 100)])
    locality = StringField('Locality in Mumbai', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(10, 15)])

    # Lifestyle
    sleep_schedule = SelectField('Sleep Schedule', choices=[
        ('', 'Select'), ('Early bird', 'Early Bird (before 10 PM)'),
        ('Flexible', 'Flexible'), ('Night owl', 'Night Owl (after midnight)')
    ], validators=[DataRequired()])
    cleanliness = SelectField('Cleanliness Level', choices=[
        ('', 'Select'), ('1', '1 - Very Messy'), ('2', '2 - Messy'),
        ('3', '3 - Average'), ('4', '4 - Clean'), ('5', '5 - Very Clean')
    ], validators=[DataRequired()])
    smoking = SelectField('Smoking', choices=[
        ('', 'Select'), ('No', 'No'), ('Occasionally', 'Occasionally'), ('Yes', 'Yes')
    ], validators=[DataRequired()])
    drinking = SelectField('Drinking', choices=[
        ('', 'Select'), ('Never', 'Never'), ('Socially', 'Socially'), ('Often', 'Often')
    ], validators=[DataRequired()])
    diet = SelectField('Diet', choices=[
        ('', 'Select'), ('Veg', 'Vegetarian'), ('Non-Veg', 'Non-Vegetarian'), ('Vegan', 'Vegan')
    ], validators=[DataRequired()])
    pets = SelectField('Pets', choices=[
        ('', 'Select'), ('Yes', 'Yes, I have/love pets'), ('No', 'No pets')
    ], validators=[DataRequired()])
    guests = SelectField('Guests Over', choices=[
        ('', 'Select'), ('Rarely', 'Rarely'), ('Sometimes', 'Sometimes'), ('Often', 'Often')
    ], validators=[DataRequired()])
    wfh_frequency = SelectField('Work From Home', choices=[
        ('', 'Select'), ('Never', 'Never'), ('1 day/week', '1 day/week'),
        ('2 days/week', '2 days/week'), ('3 days/week', '3 days/week'), ('Full-time', 'Full-time')
    ], validators=[DataRequired()])
    noise_tolerance = SelectField('Noise Tolerance', choices=[
        ('', 'Select'), ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')
    ], validators=[DataRequired()])
    sharing_pref = SelectField('Room Sharing Preference', choices=[
        ('', 'Select'), ('Private', 'Private Room'), ('Shared', 'Shared Room')
    ], validators=[DataRequired()])
    cooking = SelectField('Do you cook?', choices=[
        ('', 'Select'), ('Yes', 'Yes'), ('No', 'No')
    ], validators=[DataRequired()])
    social_style = SelectField('Social Style', choices=[
        ('', 'Select'), ('Introvert', 'Introvert'), ('Ambivert', 'Ambivert'), ('Extrovert', 'Extrovert')
    ], validators=[DataRequired()])
    communication = SelectField('Communication Style', choices=[
        ('', 'Select'), ('Polite', 'Polite'), ('Direct', 'Direct'),
        ('Friendly', 'Friendly'), ('Clear', 'Clear')
    ], validators=[DataRequired()])

    # Big Five
    openness = IntegerField('Openness (1-10)', validators=[DataRequired(), NumberRange(1, 10)])
    conscientiousness = IntegerField('Conscientiousness (1-10)', validators=[DataRequired(), NumberRange(1, 10)])
    extraversion = IntegerField('Extraversion (1-10)', validators=[DataRequired(), NumberRange(1, 10)])
    agreeableness = IntegerField('Agreeableness (1-10)', validators=[DataRequired(), NumberRange(1, 10)])
    neuroticism = IntegerField('Neuroticism (1-10)', validators=[DataRequired(), NumberRange(1, 10)])

    # Budget & Accommodation
    budget_min = IntegerField('Min Budget (₹/month)', validators=[DataRequired(), NumberRange(1000, 500000)])
    budget_max = IntegerField('Max Budget (₹/month)', validators=[DataRequired(), NumberRange(1000, 500000)])
    accommodation_type = SelectField('Accommodation Type', choices=[
        ('', 'Select'), ('PG', 'PG'), ('Flat', 'Flat'), ('Apartment', 'Apartment'),
        ('Hostel', 'Hostel'), ('Service Apartment', 'Service Apartment')
    ], validators=[DataRequired()])
    preferred_gender = SelectField('Preferred Roommate Gender', choices=[
        ('', 'Select'), ('Any', 'Any'), ('Male', 'Male'), ('Female', 'Female')
    ], validators=[DataRequired()])

    submit = SubmitField('Save Profile')


class EditProfileForm(RegistrationForm):
    looking_for = SelectField('Looking For', choices=[
        ('room', 'Looking for a Room'), ('roomate', 'Looking for a Roommate')
    ], validators=[Optional()])
    room_price = IntegerField('Room Price (₹/month)', validators=[Optional(), NumberRange(1000, 500000)])


class MessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired(), Length(1, 1000)])
    submit = SubmitField('Send')


class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '⭐⭐⭐⭐⭐ Excellent'), ('4', '⭐⭐⭐⭐ Good'),
        ('3', '⭐⭐⭐ Average'), ('2', '⭐⭐ Poor'), ('1', '⭐ Terrible')
    ], validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('general', 'General'), ('matching', 'Matching Quality'),
        ('ui', 'UI/UX'), ('bug', 'Bug Report'), ('suggestion', 'Suggestion')
    ])
    comment = TextAreaField('Comment', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Feedback')


class RoomPhotosForm(FlaskForm):
    """Upload up to 6 room photos for room owners"""
    photos = FileField('Room Photos', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only (JPG, PNG, WebP)!')
    ])
    submit = SubmitField('Upload Photos')
    
    def validate_photos(self, field):
        if field.data:
            if len(field.data) > 6:
                raise ValidationError('Maximum 6 photos allowed.')
            for photo in field.data:
                if photo.size > 5 * 1024 * 1024:
                    raise ValidationError('Each photo must be under 5MB.')
