import flask
from flask import render_template, redirect, url_for, flash, request, current_app, make_response, session
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from models import User, Comment, BlogPost
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps
from flask import abort
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, ResetRequestForm, ResetPasswordForm
from flask_gravatar import Gravatar
from randompost import random_post_process
from flask_dance.contrib.google import make_google_blueprint, google
from app import app, db, mail
from handlers import error_pages
from flask_mail import Message


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
        if not current_user.is_authenticated or current_user.id != 3:
            return abort(403)
        # Otherwise, continue with the route function
        return f(*args, **kwargs)

    return decorated_function


# db.create_all()


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


@app.route("/sitemap")
@app.route("/sitemap/")
@app.route("/sitemap.xml")
def sitemap():
    """
        Route to dynamically generate a sitemap of your website/application.
        lastmod and priority tags omitted on static pages.
        lastmod included on dynamic content such as blog posts.
    """
    from flask import make_response, request, render_template
    import datetime
    from urllib.parse import urlparse

    host_components = urlparse(request.host_url)
    host_base = host_components.scheme + "://" + host_components.netloc
    print(host_base)

    # Static routes with static content
    static_urls = list()
    for rule in app.url_map.iter_rules():
        if not str(rule).startswith("/admin") and not str(rule).startswith("/user"):
            if "GET" in rule.methods and len(rule.arguments) == 0:
                url = {
                    "loc": f"{host_base}{str(rule)}"
                }
                static_urls.append(url)

    # Dynamic routes with dynamic content
    dynamic_urls = list()
    blog_posts = BlogPost.query.all()
    for post in blog_posts:
        url = {
            "loc": f"{host_base}/post/{post.id}",
            "lastmod": post.date
        }
        dynamic_urls.append(url)

    xml_sitemap = render_template("public/sitemap.xml", static_urls=static_urls, dynamic_urls=dynamic_urls,
                                  host_base=host_base)
    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"

    return response


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
            flash("That email does not exist, please try again.", 'warning')
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.', 'warning')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/forgot_password', methods=['GET', 'POST'])
def reset_request():
    form = ResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash('Account does not exist for this email', 'warning')
            return redirect(url_for('reset_request'))
        token = User.get_token(user)
        msg = Message('Password Reset Request',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[user.email]
                      )
        msg.body = f'Hi, Password reset request received for {user.email}. Please click on following link to reset ' \
                   f'{url_for("reset_password",token=token, _external=True) }' \
                   f'\nAbove link is valid for 30 minutes only'
        mail.send(msg)
        flash("Reset Link sent. Check Email.", 'success')
        return redirect('forgot_password')   # user= current_user
    return render_template('forgot_password.html', form=form, current_user=current_user)


@app.route('/forgot_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_token(token)
    if user is None:
        flash('This is invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = generate_password_hash(form.password.data)
        db.session.commit()
        flash('Password changed', 'success')

        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


if __name__ == "__main__":
    app.run(debug=True)
