from flask import Flask
from lib import functions
import liquidity
import os

app = Flask(__name__)

#key = os.getenv("PRIVATE_KEY")

@app.route('/run_test')
def hello_runtest():
    msg = 'Running test function in liquidity.py'
    txns = liquidity.run_test()
    msg += '\n' + txns
    return msg

