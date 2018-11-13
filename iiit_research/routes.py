import os
import secrets

from flask import render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

from iiit_research import app, db, bcrypt, mail
from iiit_research.forms import RegistrationForm, CreateLabForm, LoginForm, UpdateAccountForm, PostForm, SearchForm
from iiit_research.models import User, Post, Subscription, Interest, Lab, PendingApproval


@app.route("/home")
@login_required
def home():
    user_query = db.session.query(User.id, User.username, User.name)
    join_on_user_query = user_query.join(Subscription, User.id == Subscription.followee)
    user_following = join_on_user_query.filter(Subscription.follower == current_user.id).all()
    # FIXME: this is gonna get real ugly real soon.
    user_following_ids = []
    for user in user_following:
        user_following_ids.append(user.id)

    lab_query = db.session.query(Lab.id, Lab.name)
    join_on_lab_query = lab_query.join(Subscription, Lab.id == Subscription.followee)
    lab_following = join_on_lab_query.filter(Subscription.follower == current_user.id).all()
    lab_following_ids = []
    for lab in lab_following:
        lab_following_ids.append(lab.id)

    page = request.args.get('page', 1, type=int)

    # &, | can be used inside filter boz
    # SQLAlchemy overloads the bitwise operators &, | and ~
    # so instead of the ugly and hard-to-read prefix syntax with or_() and and_() we can use these operators:
    # source: https://stackoverflow.com/a/14185275/5463404
    posts = Post.query.filter(((Post.author_type == "lab") & (Post.lab_id.in_(lab_following_ids)))
                              | ((Post.author_type == "user") & (Post.author_id.in_(user_following_ids)))).order_by(
        Post.created_at.desc()).paginate(page=page,
                                         per_page=10)

    return render_template('home.html', title='Home', posts=posts)


@app.route("/about")
@login_required
def about():
    return render_template('about.html', title='About')


@app.route("/posts")
@login_required
def post():
    posts = Post.query.all()
    return render_template('posts.html', posts=posts, title='Posts')


@app.route("/posts/<post_id>")
@login_required
def post_detail(post_id):
    """Displays a single post."""
    # TODO: change to use slug instead of id
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post, title=post.title)


def send_verify_email(user):
    print("SENDING EMAIL VERIFICATION LINK")
    token = user.generate_verification_token()
    msg = Message('Email Verification', sender='noreply@demo.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
    {url_for('verify_email', token=token, _external=True)}
    If you did not make this request then simply ignore this email and no changes will be made.'''
    mail.send(msg)


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
        send_verify_email(user)
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
            return redirect(next_page) if next_page else redirect(url_for('account'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
        # flash(f'Successfully Logged in!', 'success')
        # return redirect(url_for('home'))
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
@login_required
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


@app.route("/", methods=['GET', 'POST'])
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
        if form.prof_email.data:
            prof = User.query.filter_by(email=form.prof_email.data).first()
            if prof:
                flag = 0
                studentlist = PendingApproval.query.filter_by(prof_id=prof.id).all()
                if studentlist:
                    for student in studentlist:
                        if student.student_id == current_user.id and student.relation == False:
                            flag = 1
                            flash('Your Request is pending with  Professor for Approval!!', 'warning')
                    if flag == 0:
                        pendingapproval = PendingApproval(prof_id=prof.id, student_id=current_user.id, relation=False)
                        db.session.add(pendingapproval)
                        flash('Your Request has been submitted to Professor for Approval!', 'success')

        db.session.commit()
        flash('Your information has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.name.data = current_user.name
        form.password.data = ''
        form.confirm_password.data = ''
        form.about_me.data = current_user.about_me
        form.prof_email.data = ''

    # TODO: optimize join
    query = db.session.query(User.username, User.name, User.profile_pic)
    join_query = query.join(Subscription, User.id == Subscription.follower)
    followers = join_query.filter((Subscription.followee == current_user.id)
                                  & (Subscription.followee_type == "user")).all()

    query_user = db.session.query(User.username, User.name, User.profile_pic)
    join_query = query_user.join(Subscription, User.id == Subscription.followee)
    following_users = join_query.filter((Subscription.follower == current_user.id)
                                        & (Subscription.followee_type == "user")).all()

    query_lab = db.session.query(Lab.id, Lab.name, Lab.image)
    join_query = query_lab.join(Subscription, Lab.id == Subscription.followee)
    following_labs = join_query.filter((Subscription.follower == current_user.id)
                                       & (Subscription.followee_type == "lab")).all()

    following = following_users + following_labs

    interests = Interest.query.all()

    query = db.session.query(User.id, User.username, User.name)
    join_query = query.join(PendingApproval, User.id == PendingApproval.student_id)
    pending_student_approval_list = join_query.filter(PendingApproval.prof_id == current_user.id).all()

    proff = User.query.filter_by(id=current_user.prof_id).first()
    students = User.query.filter_by(prof_id=current_user.id).all()
    profile_pic = url_for('static', filename='profile_pics/' + current_user.profile_pic)
    return render_template('account.html', title='Account', profile_pic=profile_pic, form=form, followers=followers,
                           following=following, user=current_user, area_of_interests=interests,
                           pendingStudentApprovalList=pending_student_approval_list, students=students, prof=proff)


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
@login_required
def public_profile(username):
    """ Displays user's public profile """
    user = User.query.filter_by(username=username).first()

    if not user:
        from flask import abort
        abort(404)

    # TODO: optimize join
    query = db.session.query(User.username, User.name, User.profile_pic)
    join_query = query.join(Subscription, User.id == Subscription.follower)
    followers = join_query.filter((Subscription.followee == user.id)
                                  & (Subscription.followee_type == "user")).all()

    query_user = db.session.query(User.username, User.name, User.profile_pic)
    join_query = query_user.join(Subscription, User.id == Subscription.followee)
    following_users = join_query.filter((Subscription.follower == user.id)
                                        & (Subscription.followee_type == "user")).all()

    query_lab = db.session.query(Lab.id, Lab.name, Lab.image)
    join_query = query_lab.join(Subscription, Lab.id == Subscription.followee)
    following_labs = join_query.filter((Subscription.follower == user.id)
                                       & (Subscription.followee_type == "lab")).all()

    following = following_users + following_labs

    is_following = False  # specifies whether currently logged in user follows this user
    if current_user.is_authenticated:
        from sqlalchemy import and_
        is_following = db.session.query(
            db.exists().where(
                and_(Subscription.follower == current_user.id,
                     Subscription.followee == user.id))).scalar()

    prof = User.query.filter_by(id=current_user.prof_id).first()

    return render_template('profile.html',
                           user=user,
                           followers=followers, following=following,
                           is_following=is_following, prof=prof)


@app.route('/follow_action/<user_id>/<action>/<followee_type>')
@login_required
def follow_action(user_id, action, followee_type):
    if action == 'follow':
        row = Subscription(follower=current_user.id, followee=user_id, followee_type=followee_type)
        db.session.add(row)
        db.session.commit()
    if action == 'unfollow':
        row = Subscription.query.filter_by(follower=current_user.id, followee=user_id,
                                           followee_type=followee_type).first_or_404()
        db.session.delete(row)
        db.session.commit()

    return redirect(request.referrer)


@app.route('/approve_request/<user_id>/<action>')
@login_required
def approve_request(user_id, action):
    if action == 'accept':
        user = User.query.filter_by(id=user_id).first()
        user.prof_id = current_user.id
        row = PendingApproval.query.filter_by(prof_id=current_user.id, student_id=user_id).first_or_404()
        db.session.delete(row)
        db.session.commit()
    if action == 'delete':
        row = PendingApproval.query.filter_by(prof_id=current_user.id, student_id=user_id).first_or_404()
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
@login_required
def labs():
    labs = Lab.query.all()
    return render_template('labs.html', labs=labs)


def save_lab_image(form_pic):
    random_hex = secrets.token_hex(8)
    fname, fext = os.path.splitext(form_pic.filename)
    pic_fn = random_hex + fext
    pic_path = os.path.join(app.root_path, 'static/lab_images/', pic_fn)
    form_pic.save(pic_path)
    return pic_fn


@app.route('/labs/create', methods=['GET', 'POST'])
def create_lab():
    form = CreateLabForm()

    if form.validate_on_submit():
        print(form.image.data)
        if form.image.data:
            picture_file = save_lab_image(form.image.data)
            lab = Lab(name=form.name.data, description=form.description.data, image=picture_file)
        else:
            lab = Lab(name=form.name.data, description=form.description.data, image='default.jpg')

        current_user.lab.append(lab)
        db.session.commit()
        flash('Your lab has been created!', 'success')
        return redirect(url_for('labs'))

    return render_template('create_lab.html', title='New Lab', form=form)


@app.route('/labs/<lab_id>')
@login_required
def lab_detail(lab_id):
    lab = Lab.query.get_or_404(lab_id)

    is_following = False  # specifies whether currently logged in user follows this lab
    if current_user.is_authenticated:
        from sqlalchemy import and_
        is_following = db.session.query(
            db.exists().where(
                and_(Subscription.follower == current_user.id,
                     Subscription.followee == lab.id))).scalar()

    return render_template('lab_detail.html', lab=lab, is_following=is_following)


@app.route('/trending')
@login_required
def trending():
    top_5_posts = Post.query.order_by(Post.like_count.desc()).limit(5)

    from sqlalchemy.sql.functions import func
    from sqlalchemy import desc

    # SELECT id,username,name, followee, followee_type, count(follower) AS num_followers
    # FROM subscription,user
    # GROUP BY followee
    # ORDER BY num_followers desc
    # LIMIT 5
    most_followed = db.session.query(User.id, User.username, User.name, Subscription.followee,
                                     Subscription.followee_type,
                                     func.count(Subscription.follower).label('num_followers')) \
        .filter((Subscription.followee_type == "user") & (Subscription.followee == User.id)) \
        .group_by(Subscription.followee) \
        .order_by(desc('num_followers')).limit(5)
    return render_template('trending.html', most_liked_works=top_5_posts, most_followed=most_followed)


@app.route('/verify/<token>', methods=['GET', 'POST'])
@login_required
def verify_email(token):
    user = User.verify_token(token)
    if user is None:
        flash('That is an invalid token', 'warning')
    else:
        flash('Your email is verified', 'success')
        current_user.email_verify = True
        db.session.commit()

    return render_template('verify.html', title='Email Verification')


@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    results = set()
    if form.validate_on_submit():
        search_for = form.search_for.data
        query = form.query.data
        if search_for == "student":
            results.update(User.query.filter(User.user_type == "student")
                           .filter(User.name.like('%{0}%'.format(query))))
        elif search_for == "professor":
            results.update(
                User.query.filter(User.user_type == "professor")
                    .filter(User.name.like('%{0}%'.format(query))))
        elif search_for == "lab":
            results.update(Lab.query.filter(Lab.name.like('%{0}%'.format(query))))
        elif search_for == "area_of_interest":
            interests = Interest.query.filter(Interest.name.like('%{0}%'.format(query))).all()
            for interest in interests:
                results.update(interest.users)
    return render_template('search.html', title='Search', form=form, results=results, result_type=form.search_for.data)
