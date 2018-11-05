from datetime import datetime

from flask_login import UserMixin

from iiit_research import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}','{self.email}', '{self.image_file}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    likes = db.relationship('Like', backref='post', lazy=True)
    like_count = db.Column(db.Integer, default=0)

    # lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=True)

    def __repr__(self):
        return f"Post('{self.title}','{self.created_at}','{self.author_id}')"


class Subscription(db.Model):
    # follower = subscriber
    follower = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    # followee = publisher
    followee = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)

    from sqlalchemy import CheckConstraint

    # FIXME: Perhaps this constraint should be handled in application logic
    __table_args__ = (
        # Make sure a user can not follow himself.
        CheckConstraint(follower != followee, name='check_follower_not_followee'),
    )


class Like(db.Model):
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
