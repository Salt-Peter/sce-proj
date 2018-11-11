import os
import secrets

from flask import render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required

from iiit_research import app, db, bcrypt
from iiit_research.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from iiit_research.models import User, Post, Subscription, Interest, Lab


@app.route("/")
@app.route("/home")
@login_required
def home():
    query = db.session.query(User.id, User.username, User.name)
    join_query = query.join(Subscription, User.id == Subscription.followee)
    following = join_query.filter(Subscription.follower == current_user.id).all()
    # FIXME: this is gonna get real ugly real soon.
    following_ids = []
    for user in following:
        following_ids.append(user.id)

    page = request.args.get('page', 1, type=int)

    posts = Post.query.filter(Post.author_id.in_(following_ids)).order_by(Post.created_at.desc()).paginate(page=page,
                                                                                                           per_page=10)

    return render_template('home.html', title='Home', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/posts")
def post():
    posts = Post.query.all()
    return render_template('posts.html', posts=posts, title='Posts')


@app.route("/posts/<post_id>")
def post_detail(post_id):
    """Displays a single post."""
    # TODO: change to use slug instead of id
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post, title=post.title)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        interests = []
        for i in request.form.getlist('aoi'):
            interests.append(Interest.query.get(i))

        user = User(name=form.name.data, username=form.username.data,
                    email=form.email.data, password=hashed_password,
                    interests=interests, user_type=form.user_type.data)

        db.session.add(user)
        db.session.commit()
        flash(f'Your account is created! You can login Now.', 'success')
        return redirect(url_for('login'))
    # else:
    #     flash(f'Wrong information!', 'danger')
    # interests = db.session.query(Interest.name).all()
    interests = Interest.query.all()
    return render_template('register.html', title='Register', form=form, area_of_interests=interests)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
        # flash(f'Successfully Logged in!', 'success')
        # return redirect(url_for('home'))
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))


def save_pic(form_pic):
    random_hex = secrets.token_hex(8)
    fname, fext = os.path.splitext(form_pic.filename)
    pic_fn = random_hex + fext
    pic_path = os.path.join(app.root_path, 'static/profile_pics/', pic_fn)
    form_pic.save(pic_path)
    return pic_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_pic(form.picture.data)
            current_user.profile_pic = picture_file
        current_user.username = form.username.data
        current_user.name = form.name.data
        if form.password.data:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            current_user.password = hashed_password
        interests = []
        for i in request.form.getlist('aoi'):
            interests.append(Interest.query.get(i))
        current_user.interests = interests
        if form.about_me.data:
            current_user.about_me = form.about_me.data

        db.session.commit()
        flash('Your information has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.name.data = current_user.name
        form.password.data = ''
        form.confirm_password.data = ''
        form.about_me.data = current_user.about_me

    # TODO: optimize join
    query = db.session.query(User.username, User.name)
    join_query = query.join(Subscription, User.id == Subscription.follower)
    followers = join_query.filter(Subscription.followee == current_user.id).all()

    query = db.session.query(User.username, User.name)
    join_query = query.join(Subscription, User.id == Subscription.followee)
    following = join_query.filter(Subscription.follower == current_user.id).all()

    interests = Interest.query.all()
    profile_pic = url_for('static', filename='profile_pics/' + current_user.profile_pic)
    return render_template('account.html', title='Account', profile_pic=profile_pic, form=form, followers=followers,
                           following=following, user=current_user, area_of_interests=interests)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():

        if form.post_as.data:  # current user is a professor
            if form.post_as.data == current_user.username:  # professor is posting as himself
                author = current_user
                post = Post(title=form.title.data, content=form.content.data, author=author, author_type="user")
            else:
                author = Lab.query.get(form.post_as.data)
                post = Post(title=form.title.data, content=form.content.data, lab_author=author, author_type="lab")
        else:  # current user is a student
            post = Post(title=form.title.data, content=form.content.data, author=current_user, author_type="user")

        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)


@app.route("/user/<username>")
def public_profile(username):
    """ Displays user's public profile """
    user = User.query.filter_by(username=username).first()

    if not user:
        from flask import abort
        abort(404)

    # TODO: optimize join
    query = db.session.query(User.username, User.name)
    join_query = query.join(Subscription, User.id == Subscription.follower)
    followers = join_query.filter(Subscription.followee == user.id).all()

    query = db.session.query(User.username, User.name)
    join_query = query.join(Subscription, User.id == Subscription.followee)
    following = join_query.filter(Subscription.follower == user.id).all()

    is_following = False  # specifies whether currently logged in user follows this user
    if current_user.is_authenticated:
        from sqlalchemy import and_
        is_following = db.session.query(
            db.exists().where(
                and_(Subscription.follower == current_user.id,
                     Subscription.followee == user.id))).scalar()

    return render_template('profile.html',
                           user=user,
                           followers=followers, following=following,
                           is_following=is_following)


@app.route('/follow_action/<user_id>/<action>')
@login_required
def follow_action(user_id, action):
    if action == 'follow':
        row = Subscription(follower=current_user.id, followee=user_id)
        db.session.add(row)
        db.session.commit()
    if action == 'unfollow':
        row = Subscription.query.filter_by(follower=current_user.id, followee=user_id).first_or_404()
        db.session.delete(row)
        db.session.commit()

    return redirect(request.referrer)


@app.route('/like/<post_id>/<action>')
@login_required
def like_action(post_id, action):
    post = Post.query.get_or_404(post_id)
    if action == 'like':
        current_user.like_post(post)
        post.like_count += 1
        db.session.commit()

    if action == 'unlike':
        current_user.unlike_post(post)
        post.like_count -= 1
        db.session.commit()
    return redirect(request.referrer)


@app.route('/labs')
def labs():
    labs = Lab.query.all()
    return render_template('labs.html', labs=labs)


@app.route('/labs/<lab_id>')
def lab_detail(lab_id):
    """Displays a single post."""
    lab = Lab.query.get_or_404(lab_id)
    return render_template('lab_detail.html', lab=lab)
