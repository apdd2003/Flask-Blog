from flask import Flask
import os
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

app = Flask(__name__)

# ############ OAUTH #######
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = '1'
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = '1'

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

# CONNECT TO DB
uri = os.getenv("DATABASE_URL", "sqlite:///blog.db")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///blog.db"


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.environ.get("USER_MAIL")
app.config['MAIL_PASSWORD'] = os.environ.get("USER_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)
