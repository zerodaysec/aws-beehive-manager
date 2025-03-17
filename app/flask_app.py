from flask import Flask, request, redirect, session
import redis
import functools

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)  # Adjust parameters as needed

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get('session_token')

        # Check if session token is set and is valid
        if session_token and redis_client.get(session_token):
            return f(*args, **kwargs)
        else:
            return redirect('/login/')

    return decorated_function

@app.route('/protected/')
@login_required
def protected():
    return "This is a protected route."

@app.route('/another-protected/')
@login_required
def another_protected():
    return "This is another protected route."
