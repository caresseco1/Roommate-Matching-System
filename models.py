from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Registered users - merged with dataset profile schema."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Demographics
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    city = db.Column(db.String(100), default='Mumbai')
    locality = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    profile_pic = db.Column(db.String(255))

    # Lifestyle
    sleep_schedule = db.Column(db.String(30))   # Early bird / Night owl / Flexible
    cleanliness = db.Column(db.Integer)          # 1-5
    smoking = db.Column(db.String(20))           # No / Occasionally / Yes
    drinking = db.Column(db.String(20))          # Never / Socially / Often
    diet = db.Column(db.String(30))              # Veg / Non-Veg / Vegan
    pets = db.Column(db.String(5))               # Yes / No
    guests = db.Column(db.String(20))            # Rarely / Sometimes / Often
    wfh_frequency = db.Column(db.String(30))
    noise_tolerance = db.Column(db.String(10))   # Low / Medium / High
    sharing_pref = db.Column(db.String(10))      # Private / Shared
    cooking = db.Column(db.String(5))            # Yes / No
    social_style = db.Column(db.String(20))      # Introvert / Extrovert / Ambivert
    communication = db.Column(db.String(20))     # Direct / Polite / Friendly / Clear

    # Big Five Personality (1-10)
    openness = db.Column(db.Integer)
    conscientiousness = db.Column(db.Integer)
    extraversion = db.Column(db.Integer)
    agreeableness = db.Column(db.Integer)
    neuroticism = db.Column(db.Integer)

    # Budget & Accommodation
    budget_min = db.Column(db.Integer)
    budget_max = db.Column(db.Integer)
    accommodation_type = db.Column(db.String(50))
    preferred_gender = db.Column(db.String(20))
    looking_for = db.Column(db.String(20))       # 'room' or 'roomate'

    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    sent_requests = db.relationship('RoomRequest', foreign_keys='RoomRequest.sender_id', backref='sender', lazy='dynamic')
    received_requests = db.relationship('RoomRequest', foreign_keys='RoomRequest.receiver_id', backref='receiver', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    feedbacks = db.relationship('Feedback', backref='user', lazy='dynamic')

    @property
    def profile_completion(self):
        fields = [
            self.profile_pic, self.age, self.gender, self.occupation, self.locality, self.phone_number,
            self.sleep_schedule, self.cleanliness, self.smoking, self.drinking,
            self.diet, self.pets, self.guests, self.wfh_frequency, self.noise_tolerance,
            self.sharing_pref, self.cooking, self.social_style, self.communication,
            self.openness, self.conscientiousness, self.extraversion,
            self.agreeableness, self.neuroticism, self.budget_min, self.budget_max,
            self.accommodation_type, self.preferred_gender, self.looking_for
        ]
        filled = sum(1 for f in fields if f is not None and f != '')
        return int((filled / len(fields)) * 100)


class DatasetProfile(db.Model):
    """
    Pre-loaded profiles from the CSV dataset.
    Used as the matching pool for MLR training + candidate retrieval.
    Registered users who complete profiles are ALSO mirrored here as dataset rows.
    """
    __tablename__ = 'dataset_profiles'

    id = db.Column(db.Integer, primary_key=True)
    original_user_id = db.Column(db.Integer, unique=True, nullable=True)  # links to User.id if registered
    dataset_row_id = db.Column(db.Integer, unique=True, nullable=True)    # original CSV user_id

    name = db.Column(db.String(100))
    email = db.Column(db.String(150))
    age = db.Column(db.Float)
    gender = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    city = db.Column(db.String(100))
    locality = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    profile_pic = db.Column(db.String(255))

    sleep_schedule = db.Column(db.String(30))
    cleanliness = db.Column(db.Float)
    smoking = db.Column(db.String(20))
    drinking = db.Column(db.String(20))
    diet = db.Column(db.String(30))
    pets = db.Column(db.String(5))
    guests = db.Column(db.String(20))
    wfh_frequency = db.Column(db.String(30))
    noise_tolerance = db.Column(db.String(10))
    sharing_pref = db.Column(db.String(10))
    cooking = db.Column(db.String(5))
    social_style = db.Column(db.String(20))
    communication = db.Column(db.String(20))

    openness = db.Column(db.Float)
    conscientiousness = db.Column(db.Float)
    extraversion = db.Column(db.Float)
    agreeableness = db.Column(db.Float)
    neuroticism = db.Column(db.Float)

    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    accommodation_type = db.Column(db.String(50))
    preferred_gender = db.Column(db.String(20))
    looking_for = db.Column(db.String(20))
    room_price = db.Column(db.Float, nullable=True)


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProfileView(db.Model):
    __tablename__ = 'profile_views'

    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)


class RoomRequest(db.Model):
    __tablename__ = 'room_requests'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/accepted/declined/unmatched
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
