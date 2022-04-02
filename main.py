from flask import render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

from models import User, Comment, BlogPost
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps
from flask import abort
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from randompost import random_post_process
from flask_dance.contrib.google import make_google_blueprint, google
from app import app, db
from handlers import error_pages

google_bp = make_google_blueprint(scope=["profile", "email"])
app.register_blueprint(google_bp, url_prefix="/google-login")
app.register_blueprint(error_pages)

ckeditor = CKEditor(app)
Bootstrap(app)


gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False,
                    base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        # Otherwise, continue with the route function
        return f(*args, **kwargs)

    return decorated_function


db.create_all()


@app.route('/login/google')
def google_auth():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v1/userinfo")
    # assert resp.ok, resp.text
    user_email = resp.json()['email']
    user = User.query.filter_by(email=user_email).first()
    if user:
        login_user(user)
        return redirect(url_for("get_all_post"))
    else:
        new_user = User(email=user_email,
                        name=resp.json()['name'])
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)

    return redirect(url_for("get_all_post"))


# Register new users into the User database
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # If user's email already exists
        if User.query.filter_by(email=form.email.data).first():
            # Send flash messsage
            flash("You've already signed up with that email, log in instead!")
            # Redirect to /login route.
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/')
def get_all_posts():
    if google.authorized:
        resp = google.get("/oauth2/v1/userinfo")
        # assert resp.ok, resp.text
        user_email = resp.json()['email']
        user = User.query.filter_by(email=user_email).first()
        if user:
            login_user(user)
    page = request.args.get('page', 1, type=int)
    posts = BlogPost.query.order_by(BlogPost.id.desc()).paginate(page=page, per_page=5)

    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/logout')
def logout():
    if google.authorized:
        token = google_bp.token["access_token"]
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.ok, resp.text
        del google_bp.token  # Delete OAuth token from storage
    logout_user()  # Delete Flask-Login's session cookie

    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post, form=form, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=['POST', 'GET'])
# Mark with decorator
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/random-post", methods=['POST', 'GET'])
# Mark with decorator
@admin_only
def add_random_post():
    random_post_title, random_post_subtitle, random_post_img, random_post_content = random_post_process()
    form = CreatePostForm(
        title=random_post_title,
        subtitle=random_post_subtitle,
        body=random_post_content,
        img_url=random_post_img,
    )
    # current_user.__name='bot'
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,

            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=['POST', 'GET'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))

    return render_template("login.html", form=form, current_user=current_user)


if __name__ == "__main__":
    app.run(debug=True)