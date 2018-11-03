from flask import render_template

from app import app


@app.route("/hello/", methods=['GET'])
def hello():
    return render_template('hello.html')
