from functools import wraps
from flask import session, redirect


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def image_format(list, str):
    return next(s for s in list if s in str)


def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False
