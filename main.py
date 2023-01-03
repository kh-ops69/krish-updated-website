from flask import Flask, render_template, redirect, url_for, flash, request,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, String, Column
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm
from flask_gravatar import Gravatar
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, DataRequired
from flask_wtf import FlaskForm
from functools import wraps
from flask_ckeditor import CKEditorField


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['CKEDITOR_PKG_TYPE'] = 'full'
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=60,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@login_manager.user_loader
def load_user(user_id):
    return CreateUsers.query.get(int(user_id))

def check_decorator(function):
    @wraps(function)
    def admin_only(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)
    return admin_only


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class BlogPost(UserMixin, db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = Column(String(250), ForeignKey('new_users.Name'))
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    parent = relationship("CreateUsers", back_populates="children")
    grand_parent = relationship("UserComments", back_populates="grandkid")

db.create_all()


class CreateUsers(UserMixin, db.Model):
    __tablename__ = "new_users"
    id = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(250), nullable=False, unique=True)
    Name = db.Column(db.String(250), nullable=False)
    Password = db.Column(db.String(250), nullable=False)
    children = relationship("BlogPost", back_populates="parent")
    father = relationship("UserComments", back_populates="child_two")

db.create_all()


class UserComments(UserMixin, db.Model):
    __tablename__ = "user_comments"
    id = db.Column(db.Integer, primary_key=True)
    name = Column(db.Integer, ForeignKey("new_users.Name"))
    blog_post = Column(db.Integer, ForeignKey("blog_posts.title"))
    body = db.Column(db.String(500), nullable=False)
    child_two = relationship("CreateUsers", back_populates="father")
    grandkid = relationship("BlogPost", back_populates="grand_parent")

db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    try:
        print(current_user.id)
    except AttributeError:
        pass
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, user=current_user)


class RegisterForm(FlaskForm):
    Email = StringField('Email ID', validators=[InputRequired()])
    Name = StringField('Name', validators=[InputRequired()])
    Password = StringField('Password', validators=[InputRequired()])
    submit = SubmitField('Add User')


class LogInForm(FlaskForm):
    Email = StringField('Email ID', validators=[InputRequired()])
    Password = StringField('Password', validators=[InputRequired()])
    submit = SubmitField('Add User')

class CommentForm(FlaskForm):
    body = CKEditorField('Comment:', validators=[DataRequired()])
    submit = SubmitField('Submit Comment')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        new_user = CreateUsers(Email=request.form.get('Email'), Name=request.form.get('Name'),
                               Password=generate_password_hash(request.form.get('Password'), method='pbkdf2:sha256',
                                                               salt_length=8))
        if CreateUsers.query.filter_by(Email=request.form.get('Email')).first():
            flash('this email is already registered!')
            return redirect(url_for('login'))
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login = LogInForm()
    if request.method == 'POST':
        user = CreateUsers.query.filter_by(Email=login.Email.data).first()
        user_log_psw = login.Password.data
        if user is not None:
            if check_password_hash(user.Password, user_log_psw):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('password is incorrect!')
                return redirect(url_for('login'))
        else:
            flash('user not registered!')
            # if user.id == 1:
            #     posts = BlogPost.query.all()
            #     return render_template('index.html', logged_in=current_user.is_authenticated, all_posts=posts)
            # else:
            #     return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=login, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    commens = UserComments.query.all()
    requested_post = BlogPost.query.get(post_id)
    comment_data = request.form.get('body')
    try:
        user = current_user.Name
    except AttributeError:
        pass
    blog_title = BlogPost.query.get('title')
    print(comment_data)
    # print(requested_post.title)  how to access specific element of a particular database
    if request.method == 'POST':
        new_comment = UserComments(name=user, blog_post=requested_post.title, body=comment_data)
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated,
                           user=current_user, comment=CommentForm(), comments = commens)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post")
@check_decorator
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
    return render_template("make-post.html", form=form)

@check_decorator
@app.route("/edit-post/<int:post_id>")
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
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)

@check_decorator
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)