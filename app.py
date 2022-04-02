# from main import app
from flask import Flask
import os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ############ OAUTH #######
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = '1'
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = '1'

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

#############################

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
# print(os.environ.get("SECRET_KEY"))
# ckeditor = CKEditor(app)
# Bootstrap(app)

# CONNECT TO DB
uri = os.getenv("DATABASE_URL", "sqlite:///blog.db")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_DATABASE_URI'] = uri


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
