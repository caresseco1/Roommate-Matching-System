"""
StayMate — app.py
=================
Main Flask application.  All routes, auth, matching, messaging, requests,
notifications, and admin live here.
"""

import os
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

from flask import (Flask, render_template, redirect, url_for, flash,
                   session, request, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_mail import Mail, Message as MailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

# ── App factory ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///staymate.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file upload size

# Mail config (Gmail SMTP; falls back to console print if not configured)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'noreply@staymate.in')

from models import db, User, DatasetProfile, Message, ProfileView, RoomRequest, Notification, Feedback, RoomPhoto
from forms import (SignupForm, LoginForm, OTPForm, LookingForForm,
                   RegistrationForm, EditProfileForm, MessageForm, FeedbackForm, RoomPhotosForm)
import matching

db.init_app(app)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

OTP_EXPIRY_MINUTES = 10


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── Helpers ──────────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def send_email(to, subject, body):
    try:
        msg = MailMessage(subject, recipients=[to], body=body)
        mail.send(msg)
    except Exception as e:
        print(f"[MAIL FALLBACK] To: {to}\nSubject: {subject}\n{body}\nError: {e}")


def generate_otp(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def notify(user_id, message, link=None):
    n = Notification(user_id=user_id, message=message, link=link)
    db.session.add(n)
    db.session.commit()


def _all_dataset_profiles():
    return DatasetProfile.query.all()


def _sync_user_to_dataset(user: User):
    """
    Keep the dataset_profiles table in sync with the registered user's profile
    so the MLR model always includes real users in the matching pool.
    """
    existing = DatasetProfile.query.filter_by(original_user_id=user.id).first()
    data = dict(
        original_user_id=user.id,
        name=user.username,
        email=user.email,
        age=user.age,
        gender=user.gender,
        occupation=user.occupation,
        city=user.city or 'Mumbai',
        locality=user.locality,
        phone_number=user.phone_number,
        profile_pic=user.profile_pic,
        sleep_schedule=user.sleep_schedule,
        cleanliness=user.cleanliness,
        smoking=user.smoking,
        drinking=user.drinking,
        diet=user.diet,
        pets=user.pets,
        guests=user.guests,
        wfh_frequency=user.wfh_frequency,
        noise_tolerance=user.noise_tolerance,
        sharing_pref=user.sharing_pref,
        cooking=user.cooking,
        social_style=user.social_style,
        communication=user.communication,
        openness=user.openness,
        conscientiousness=user.conscientiousness,
        extraversion=user.extraversion,
        agreeableness=user.agreeableness,
        neuroticism=user.neuroticism,
        budget_min=user.budget_min,
        budget_max=user.budget_max,
        accommodation_type=user.accommodation_type,
        preferred_gender=user.preferred_gender,
        looking_for=user.looking_for,
    )
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        existing = DatasetProfile(**data)
        db.session.add(existing)
    db.session.commit()
    matching.invalidate_cache()


# ── Context processor (navbar counts) ────────────────────────────────────────

@app.context_processor
def inject_counts():
    if current_user.is_authenticated:
        unread_msgs = Message.query.filter_by(
            receiver_id=current_user.id, is_read=False).count()
        pending_reqs = RoomRequest.query.filter_by(
            receiver_id=current_user.id, status='pending').count()
        unread_notifs = Notification.query.filter_by(
            user_id=current_user.id, is_read=False).count()
        return dict(unread_msgs=unread_msgs, pending_reqs=pending_reqs, unread_notifs=unread_notifs)
    return dict(unread_msgs=0, pending_reqs=0, unread_notifs=0)


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/')
def welcome():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('welcome.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = SignupForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        otp = generate_otp()
        session['pending_signup'] = {
            'username': form.username.data,
            'email': form.email.data.lower(),
            'password_hash': generate_password_hash(form.password.data),
            'otp': otp,
            'otp_expiry': (datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat(),
        }
        send_email(form.email.data, 'StayMate — Verify Your Email',
                   f'Your OTP is: {otp}\nValid for {OTP_EXPIRY_MINUTES} minutes.')
        flash('OTP sent to your email!', 'success')
        return redirect(url_for('verify'))
    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_verified:
                flash('Please verify your email first.', 'warning')
                return redirect(url_for('verify'))
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    form = OTPForm()
    pending = session.get('pending_signup')

    if form.validate_on_submit():
        if not pending:
            flash('Session expired. Please sign up again.', 'danger')
            return redirect(url_for('signup'))

        expiry = datetime.fromisoformat(pending['otp_expiry'])
        if datetime.utcnow() > expiry:
            flash('OTP expired. Please request a new one.', 'danger')
            return redirect(url_for('resend_otp'))

        if form.otp.data == pending['otp']:
            user = User(
                username=pending['username'],
                email=pending['email'],
                password_hash=pending['password_hash'],
                is_verified=True,
            )
            db.session.add(user)
            db.session.commit()
            session.pop('pending_signup', None)
            login_user(user)
            flash('Account verified! Choose what you are looking for.', 'success')
            return redirect(url_for('looking_for'))
        else:
            flash('Incorrect OTP. Try again.', 'danger')

    return render_template('verify.html', form=form)


@app.route('/resend-otp')
def resend_otp():
    pending = session.get('pending_signup')
    if not pending:
        flash('No pending signup. Please start again.', 'danger')
        return redirect(url_for('signup'))
    otp = generate_otp()
    pending['otp'] = otp
    pending['otp_expiry'] = (datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    session['pending_signup'] = pending
    send_email(pending['email'], 'StayMate — New OTP',
               f'Your new OTP is: {otp}\nValid for {OTP_EXPIRY_MINUTES} minutes.')
    flash('New OTP sent!', 'success')
    return redirect(url_for('verify'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('welcome'))


# ── Onboarding ────────────────────────────────────────────────────────────────

@app.route('/looking-for', methods=['GET', 'POST'])
@login_required
def looking_for():
    # Skip if already set
    if current_user.looking_for:
        return redirect(url_for('dashboard'))
    
    form = LookingForForm()
    if form.validate_on_submit():
        current_user.looking_for = form.looking_for.data
        db.session.commit()
        _sync_user_to_dataset(current_user)
        flash('Profile complete! Here are your matches.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('looking_for.html', form=form)


@app.route('/registration', methods=['GET', 'POST'])
@login_required
def registration():
    form = RegistrationForm(obj=current_user)
    if form.validate_on_submit():
        # Process profile picture upload safely
        if form.profile_pic.data and hasattr(form.profile_pic.data, 'filename'):
            pic = form.profile_pic.data
            filename = secure_filename(pic.filename)
            if filename:
                filename = f"user_{current_user.id}_{filename}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                pic.save(os.path.join(upload_dir, filename))
                current_user.profile_pic = filename
        current_user.age = form.age.data
        current_user.gender = form.gender.data
        current_user.occupation = form.occupation.data
        current_user.locality = form.locality.data
        current_user.phone_number = form.phone_number.data
        current_user.sleep_schedule = form.sleep_schedule.data
        current_user.cleanliness = int(form.cleanliness.data)
        current_user.smoking = form.smoking.data
        current_user.drinking = form.drinking.data
        current_user.diet = form.diet.data
        current_user.pets = form.pets.data
        current_user.guests = form.guests.data
        current_user.wfh_frequency = form.wfh_frequency.data
        current_user.noise_tolerance = form.noise_tolerance.data
        current_user.sharing_pref = form.sharing_pref.data
        current_user.cooking = form.cooking.data
        current_user.social_style = form.social_style.data
        current_user.communication = form.communication.data
        current_user.openness = form.openness.data
        current_user.conscientiousness = form.conscientiousness.data
        current_user.extraversion = form.extraversion.data
        current_user.agreeableness = form.agreeableness.data
        current_user.neuroticism = form.neuroticism.data
        current_user.budget_min = form.budget_min.data
        current_user.budget_max = form.budget_max.data
        current_user.accommodation_type = form.accommodation_type.data
        current_user.preferred_gender = form.preferred_gender.data
        if current_user.looking_for in ['roomate', 'roomate']:
            current_user.room_price = form.room_price.data
        db.session.commit()
        _sync_user_to_dataset(current_user)
        return redirect(url_for('dashboard'))
    return render_template('registration.html', form=form)


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        # Save existing picture because populate_obj will overwrite it
        existing_pic = current_user.profile_pic
        
        form.populate_obj(current_user)
        
        # Process new profile picture upload safely
        if form.profile_pic.data and hasattr(form.profile_pic.data, 'filename') and form.profile_pic.data.filename:
            pic = form.profile_pic.data
            filename = secure_filename(pic.filename)
            if filename:
                filename = f"user_{current_user.id}_{filename}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                pic.save(os.path.join(upload_dir, filename))
                current_user.profile_pic = filename
        else:
            current_user.profile_pic = existing_pic

        current_user.cleanliness = int(form.cleanliness.data)

        db.session.commit()
        _sync_user_to_dataset(current_user)
        flash('Profile updated!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_profile.html', form=form)


@app.route('/upload-room-photos', methods=['GET', 'POST'])
@login_required
def upload_room_photos():
    if current_user.looking_for not in ['roomate', 'roomate']:
        flash('Room photos available for room owners only.', 'warning')
        return redirect(url_for('edit_profile'))
    
    form = RoomPhotosForm()
    if form.validate_on_submit():
        room_dir = os.path.join(app.root_path, 'static', 'uploads', 'room-photos', f'user_{current_user.id}')
        os.makedirs(room_dir, exist_ok=True)
        
        # Handle multiple files from getlist
        files = request.files.getlist('photos')
        uploaded_count = 0
        current_count = RoomPhoto.query.filter_by(user_id=current_user.id).count()
        
        for photo in files:
            if photo.filename:  # Only process uploaded files
                if current_count + uploaded_count >= 6:
                    flash('Maximum limit of 6 photos reached. Some photos were not uploaded.', 'warning')
                    break
                filename = secure_filename(photo.filename)
                if filename:
                    unique_name = f"{secrets.token_hex(8)}_{filename}"
                    photo.save(os.path.join(room_dir, unique_name))
                    
                    new_photo = RoomPhoto(
                        user_id=current_user.id,
                        filename=f"uploads/room-photos/user_{current_user.id}/{unique_name}"
                    )
                    db.session.add(new_photo)
                    uploaded_count += 1
        
        if uploaded_count > 0:
            db.session.commit()
            flash(f'Uploaded {uploaded_count} room photo(s)!', 'success')
        elif current_count < 6 and not any(p.filename for p in files):
            flash('No photos selected.', 'warning')
        return redirect(url_for('upload_room_photos'))
    
    # Show current photos
    user_photos = RoomPhoto.query.filter_by(user_id=current_user.id)\
        .order_by(RoomPhoto.uploaded_at.desc()).all()
    return render_template('room_photos.html', form=form, photos=user_photos)

@app.route('/delete-room-photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_room_photo(photo_id):
    photo = RoomPhoto.query.get_or_404(photo_id)
    if photo.user_id != current_user.id:
        flash('Not authorised to delete this photo.', 'danger')
        return redirect(url_for('upload_room_photos'))
    
    try:
        file_path = os.path.join(app.root_path, 'static', photo.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
        
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted successfully.', 'success')
    return redirect(url_for('upload_room_photos'))


# ── Dashboard & Matching ──────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    profiles = _all_dataset_profiles()
    top_matches = []
    if current_user.profile_completion >= 50:
     top_matches = matching.get_matches(current_user, profiles, top_n=12)

    # Preprocess map_data for clean JSON in template (fixes VSCode JS errors)
    map_data = []
    for m in top_matches:
        p = m['profile']
        map_data.append({
            "name": getattr(p, 'name', 'Anonymous') or "Anonymous",
            "locality": getattr(p, 'locality', getattr(p, 'city', 'Mumbai')) or "Mumbai",
            "score": m['final_score'],
            "url": url_for("profile_dataset", dp_id=p.id)
        })

    pending_requests = RoomRequest.query.filter_by(
        receiver_id=current_user.id, status='pending').order_by(RoomRequest.created_at.desc()).all()
        
    pending_sent_count = RoomRequest.query.filter_by(
        sender_id=current_user.id, status='pending').count()
    total_pending_requests = len(pending_requests) + pending_sent_count
    
    sent_msgs = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id).distinct()
    received_msgs = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id).distinct()
    active_chats_count = len(set([r[0] for r in sent_msgs] + [r[0] for r in received_msgs]))
        
    unread_msgs_raw = Message.query.filter_by(
        receiver_id=current_user.id, is_read=False).order_by(Message.sent_at.desc()).all()
        
    unread_messages = []
    seen_senders = set()
    for msg in unread_msgs_raw:
        if msg.sender_id not in seen_senders:
            unread_messages.append(msg)
            seen_senders.add(msg.sender_id)

    return render_template('dashboard.html',
                           user=current_user,
                           top_matches=top_matches,
                           map_data=map_data,
                           pending_requests=pending_requests,
                           total_pending_requests=total_pending_requests,
                           active_chats_count=active_chats_count,
                           unread_messages=unread_messages,
                           profile_completion=current_user.profile_completion)


@app.route('/matches')
@login_required
def matches():
    sort_by = request.args.get('sort_by', 'compatibility')
    profiles = _all_dataset_profiles()
    all_matches = matching.get_matches(current_user, profiles, top_n=300, sort_by=sort_by)
    return render_template('matches.html', matches=all_matches, sort_by=sort_by)


# ── Profile view ──────────────────────────────────────────────────────────────

@app.route('/profile/dataset/<int:dp_id>')
@login_required
def profile_dataset(dp_id):
    """View a dataset profile (non-registered user)."""
    dp = DatasetProfile.query.get_or_404(dp_id)
    compat = matching.get_compatibility(current_user, dp, _all_dataset_profiles())

    room_photos = []
    # If the dataset profile is a real user, track the view
    if dp.original_user_id:
        pv = ProfileView(viewer_id=current_user.id, viewed_id=dp.original_user_id)
        db.session.add(pv)
        db.session.commit()
        room_photos = RoomPhoto.query.filter_by(user_id=dp.original_user_id).all()

    return render_template('profile_dataset.html', dp=dp, compat=compat, room_photos=room_photos)


@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    """View a registered user's profile."""
    viewed_user = User.query.get_or_404(user_id)
    pv = ProfileView(viewer_id=current_user.id, viewed_id=user_id)
    db.session.add(pv)
    db.session.commit()
    compat = matching.get_compatibility(current_user, viewed_user, _all_dataset_profiles())
    room_photos = RoomPhoto.query.filter_by(user_id=user_id).all()
    return render_template('profile.html', viewed=viewed_user, compat=compat, room_photos=room_photos)


# ── Messaging ─────────────────────────────────────────────────────────────────

@app.route('/messages')
@login_required
def messages():
    # Distinct conversations
    sent = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id).distinct()
    received = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id).distinct()
    partner_ids = set([r[0] for r in sent] + [r[0] for r in received])
    partners = User.query.filter(User.id.in_(partner_ids)).all()
    
    conversations = []
    for p in partners:
        last_msg = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == p.id)) |
            ((Message.sender_id == p.id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.sent_at.desc()).first()
        unread = Message.query.filter_by(sender_id=p.id, receiver_id=current_user.id, is_read=False).count()
        conversations.append({'partner': p, 'last_msg': last_msg, 'unread': unread})
        
    conversations.sort(key=lambda x: x['last_msg'].sent_at if x['last_msg'] else datetime.min, reverse=True)
    return render_template('messages.html', conversations=conversations)


@app.route('/messages/<int:other_id>', methods=['GET', 'POST'])
@login_required
def chat(other_id):
    other = User.query.get_or_404(other_id)

    # Check for accepted match to allow messaging
    is_matched = RoomRequest.query.filter(
        (
            ((RoomRequest.sender_id == current_user.id) & (RoomRequest.receiver_id == other_id)) |
            ((RoomRequest.sender_id == other_id) & (RoomRequest.receiver_id == current_user.id))
        ),
        RoomRequest.status == 'accepted'
    ).first()

    form = MessageForm()
    if form.validate_on_submit():
        if is_matched:
            msg = Message(sender_id=current_user.id, receiver_id=other_id,
                          content=form.content.data)
            db.session.add(msg)
            db.session.commit()
            form.content.data = ''
        else:
            flash('You must have an accepted request to send messages.', 'danger')

    # Mark received as read
    Message.query.filter_by(sender_id=other_id, receiver_id=current_user.id,
                             is_read=False).update({'is_read': True})
    db.session.commit()

    msgs = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_id)) |
        ((Message.sender_id == other_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.sent_at.asc()).all()

    return render_template('chat.html', other=other, messages=msgs, form=form, is_matched=is_matched)


@app.route('/api/unread-count')
@login_required
def unread_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@app.route('/message/delete/<int:msg_id>', methods=['POST'])
@login_required
def delete_message(msg_id):
    msg = Message.query.get_or_404(msg_id)
    if msg.sender_id != current_user.id:
        flash('Not authorised to delete this message.', 'danger')
        return redirect(request.referrer or url_for('messages'))
    db.session.delete(msg)
    db.session.commit()
    return redirect(request.referrer or url_for('messages'))


# ── Room Requests & Chat Initiation ──────────────────────────────────────────

@app.route('/message/start/<int:receiver_id>', methods=['POST'])
@login_required
def start_chat(receiver_id):
    """
    Initiate a chat/request. Creates a RoomRequest if one doesn't exist,
    then redirects appropriately based on match status.
    """
    receiver = User.query.get_or_404(receiver_id)
    if receiver.id == current_user.id:
        return redirect(url_for('dashboard'))

    # Find existing request (in any direction)
    existing_request = RoomRequest.query.filter(
        ((RoomRequest.sender_id == current_user.id) & (RoomRequest.receiver_id == receiver_id)) |
        ((RoomRequest.sender_id == receiver_id) & (RoomRequest.receiver_id == current_user.id))
    ).first()

    if not existing_request:
        req = RoomRequest(sender_id=current_user.id, receiver_id=receiver_id)
        db.session.add(req)
        db.session.commit()
        notify(
            receiver_id, f'{current_user.username} sent you a message request!',
            url_for('room_requests')
        )
        send_email(
            receiver.email, 'StayMate — New Message Request',
            f'Hi {receiver.username},\n{current_user.username} wants to connect on StayMate!')
        flash('Message request sent! You can chat once they accept.', 'success')
        return redirect(url_for('room_requests'))
        
    elif existing_request.status == 'accepted':
        return redirect(url_for('chat', other_id=receiver_id))
        
    elif existing_request.status == 'pending':
        if existing_request.receiver_id == current_user.id:
            # They sent a request to us, we clicked "Message". Auto-accept it!
            existing_request.status = 'accepted'
            db.session.commit()
            notify(
                existing_request.sender_id,
                f'{current_user.username} accepted your request! You can now chat.',
                url_for('chat', other_id=current_user.id)
            )
            flash(f'You accepted {receiver.username}\'s request! You can now chat.', 'success')
            return redirect(url_for('chat', other_id=receiver_id))
        else:
            flash('Message request already sent! Waiting for their approval.', 'info')
            return redirect(url_for('room_requests'))

    elif existing_request.status in ['declined', 'unmatched']:
        # Allow re-requesting by resetting the status
        existing_request.status = 'pending'
        existing_request.sender_id = current_user.id
        existing_request.receiver_id = receiver_id
        existing_request.updated_at = datetime.utcnow()
        db.session.commit()
        notify(
            receiver_id, f'{current_user.username} sent you a new message request!',
            url_for('room_requests')
        )
        flash('New message request sent! You can chat once they accept.', 'success')
        return redirect(url_for('room_requests'))

    return redirect(url_for('room_requests'))


@app.route('/room-requests')
@login_required
def room_requests():
    sent = RoomRequest.query.filter_by(sender_id=current_user.id).all()
    received = RoomRequest.query.filter_by(receiver_id=current_user.id).all()
    return render_template('room_requests.html', sent=sent, received=received)


@app.route('/room-request/accept/<int:req_id>', methods=['POST'])
@login_required
def accept_request(req_id):
    req = RoomRequest.query.get_or_404(req_id)
    if req.receiver_id != current_user.id and not current_user.is_admin:
        flash('Not authorised.', 'danger')
        return redirect(url_for('room_requests'))
    req.status = 'accepted'
    db.session.commit()
    sender = db.session.get(User, req.sender_id)
    receiver = db.session.get(User, req.receiver_id)
    
    notify(
        req.sender_id,
        f'{receiver.username} accepted your request! You can now see their contact details in the chat.',
        url_for('chat', other_id=receiver.id)
    )
    if current_user.is_admin:
        notify(
            req.receiver_id,
            f'Admin accepted the request from {sender.username} on your behalf.',
            url_for('chat', other_id=sender.id)
        )
        
    send_email(
        sender.email, 'StayMate — Request Accepted',
        f'Great news! {receiver.username} accepted your message request. You can now view their contact details by starting a chat.'
    )
    flash('Request accepted! You can now chat and view contact details.', 'success')
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('room_requests'))


@app.route('/room-request/decline/<int:req_id>', methods=['POST'])
@login_required
def decline_request(req_id):
    req = RoomRequest.query.get_or_404(req_id)
    if req.receiver_id != current_user.id and not current_user.is_admin:
        flash('Not authorised.', 'danger')
        return redirect(url_for('room_requests'))
    req.status = 'declined'
    db.session.commit()
    flash('Request declined.', 'info')
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('room_requests'))


@app.route('/room-request/unmatch/<int:req_id>', methods=['POST'])
@login_required
def unmatch(req_id):
    req = RoomRequest.query.get_or_404(req_id)
    if req.sender_id != current_user.id and req.receiver_id != current_user.id:
        flash('Not authorised.', 'danger')
        return redirect(url_for('room_requests'))
    other_id = req.receiver_id if req.sender_id == current_user.id else req.sender_id
    req.status = 'unmatched'
    db.session.commit()
    notify(other_id,
           f'{current_user.username} unmatched with you.',
           url_for('room_requests'))
    flash('Unmatched successfully.', 'info')
    return redirect(url_for('room_requests'))


@app.route('/room-request/dataset/<int:dp_id>', methods=['POST'])
@login_required
def send_room_request_dataset(dp_id):
    "Send room request/interest for dataset profile (non-registered). Logs as notification to self and admin email."
    dp = DatasetProfile.query.get_or_404(dp_id)
    if dp.original_user_id == current_user.id:
        flash('Cannot request your own profile.', 'warning')
        return redirect(url_for('profile_dataset', dp_id=dp_id))
    
    message = f'Interested in profile "{dp.name or "Anonymous"}" (DP ID: {dp_id}) from {current_user.username}'
    
    # Notify current user
    notify(current_user.id, message, url_for('matches'))
    
    # Admin email fallback
    admin_email = 'staymateapp19@gmail.com'
    send_email(admin_email, 'StayMate — New Dataset Interest', message)
    
    flash('Interest sent for this profile! You\'ll be notified if they register.', 'success')
    return redirect(url_for('profile_dataset', dp_id=dp_id))



# ── Notifications ─────────────────────────────────────────────────────────────

@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(
        user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)


# ── Feedback ──────────────────────────────────────────────────────────────────

@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        fb = Feedback(
            user_id=current_user.id,
            rating=int(form.rating.data),
            comment=form.comment.data,
            category=form.category.data,
        )
        db.session.add(fb)
        db.session.commit()
        send_email('staymateapp19@gmail.com', f'StayMate Feedback — {form.category.data}',
                   f'From: {current_user.email}\nRating: {form.rating.data}/5\n\n{form.comment.data}')
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('feedback.html', form=form)


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route('/admin/refresh-engine', methods=['POST'])
@admin_required
def admin_refresh_engine():
    matching.invalidate_cache()
    flash('Matching engine cache cleared! The MLR model will retrain with your new weights on the next request.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.created_at >= seven_days_ago).count()
    
    total_requests = RoomRequest.query.count()
    pending_requests = RoomRequest.query.filter_by(status='pending').count()
    
    recent_requests = RoomRequest.query.order_by(RoomRequest.created_at.desc()).limit(10).all()
    
    return render_template('admin_dashboard.html', total_users=total_users, new_users=new_users,
                           total_requests=total_requests, pending_requests=pending_requests,
                           recent_requests=recent_requests)


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('admin_feedback.html', feedbacks=feedbacks)


# ── Init ──────────────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File is too large! Please upload an image smaller than 16MB.', 'danger')
    return redirect(request.url)


@app.cli.command('init-db')
def init_db():
    """Create all tables and load dataset."""
    db.create_all()
    print('Database tables created.')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Auto-create a default admin user on startup if it doesn't exist
        if not User.query.filter_by(email='admin@staymate.in').first():
            admin = User(
                username='Admin',
                email='admin@staymate.in',
                password_hash=generate_password_hash('admin123'),
                is_verified=True,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
