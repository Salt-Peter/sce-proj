from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint

from iiit_research import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# http://flask-sqlalchemy.pocoo.org/2.3/models/#many-to-many-relationships
# A mapping between user and area of interests
UserInterests = db.Table(
    'user_interests',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    user_type = db.Column(db.String(10), nullable=False, default='student')
    about_me = db.Column(db.String(500),nullable=True)
    interests = db.relationship('Interest', secondary=UserInterests, lazy='subquery',
                                backref=db.backref('users', lazy=True))
    


    def like_post(self, post):
        if not self.has_liked_post(post):
            like = Like(user_id=self.id, post_id=post.id)
            db.session.add(like)

    def unlike_post(self, post):
        if self.has_liked_post(post):
            Like.query.filter_by(
                user_id=self.id,
                post_id=post.id).delete()

    def has_liked_post(self, post):
        return Like.query.filter(
            Like.user_id == self.id,
            Like.post_id == post.id).count() > 0

    def __repr__(self):
        return f"User('{self.username}','{self.email}', '{self.profile_pic}')"


class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(20))


class LabMembers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class LabAdmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    likes = db.relationship('Like', backref='post', lazy=True)
    like_count = db.Column(db.Integer, default=0)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=True)

    def __repr__(self):
        return f"Post('{self.title}','{self.created_at}','{self.author_id}')"


# follower = subscriber followee = publisher
class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    followee = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # FIXME: Perhaps this constraint should be handled in application logic
    __table_args__ = (
        # Make sure a user can not follow himself.
        CheckConstraint(follower != followee, name='check_follower_not_followee'),
        UniqueConstraint('follower', 'followee', name='follower_followee_unique'),
    )


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='post_user_like_unique'),
    )


class Interest(db.Model):
    """Possible areas of interest user can choose from"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)

class PendingApproval(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    prof_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (
        # Make sure a user can not follow himself.
        CheckConstraint(prof_id != student_id, name='check_student_not_prof'),
        UniqueConstraint('prof_id', 'student_id', name='student_prof_unique'),
    )