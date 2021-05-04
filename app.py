from flask import Flask
from lib import functions

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/run_test')
def hello_runtest():
    msg = 'Hello! This is the run_test route'
    return msg

@app.route('/safe_add')
def hello_safeadd():
    sum = functions.safe_add(1+2)
    msg = f'Hello! This is the safe_add route\n, 1 + 2 = {sum}'
    return msg
