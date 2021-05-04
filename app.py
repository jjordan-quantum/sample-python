from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello Sammy!'

@app.route('/runtest')
def hello_runtest():
    return 'Hello! This is the runtest route'
