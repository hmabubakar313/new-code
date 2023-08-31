from flask import (
    Flask,
    redirect,
    render_template,
    request,
    g,
    session,
    url_for,
    Response,
    jsonify
)
import cv2
import time
import json
import pyrebase
import pandas as pd
from jinja2 import Environment
from model.modelTest import execute
from werkzeug.utils import secure_filename
from jinja2.loaders import FileSystemLoader


app = Flask(__name__)
app.secret_key = 'secretkey'


#config = {
#    'apiKey': "AIzaSyCHNvkHyXtD0o6PBduO1bynM0IiyaY1Nbc",
#    'authDomain': "shooting-range-flask.firebaseapp.com",
#    "databaseURL": "https://shooting-range-flask-default-rtdb.firebaseio.com",
#    'projectId': "shooting-range-flask",
#    'storageBucket': "shooting-range-flask.appspot.com",
#    'messagingSenderId': "391164703988",
#    'appId': "1:391164703988:web:e23fc13d93a34e20aa9aa1",
#    'measurementId': "G-C3N6HDKE82",
#}

config = {
    'apiKey': "AIzaSyBDZ9uKXSE9lOVlqK_RRakVFtOet92cH28",
    'authDomain': "bullet-detection.firebaseapp.com",
    "databaseURL": "https://bullet-detection-default-rtdb.firebaseio.com",
    'projectId': "bullet-detection",
    'storageBucket': "bullet-detection.appspot.com",
    'messagingSenderId': "687979279540",
    'appId': "1:687979279540:web:25ae0fa76ada1e7a3dd3e1",
    'measurementId': "G-Z1LQ6YC1NK"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()

VideoPath = ''


def dumpSession():
    session.pop('user', None)


def tableGenertor():
    df = pd.read_json('data.json').T
    df.drop_duplicates(subset='Distance', keep='first', inplace=True)
    return df


def gen_real_frames(path):
    cam = cv2.VideoCapture(path)
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/real_video/<path:pathToFile>')
def real_video(pathToFile):
    return Response(gen_real_frames(pathToFile),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def gen_derivative_frames(VideoPath):
    cam = cv2.VideoCapture(VideoPath)
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_image = cv2.GaussianBlur(gray_image, (7, 7), 0)
            edges = cv2.Canny(gray_image, 50, 100)
            ret, buffer = cv2.imencode('.jpg', edges)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/derivative_video/<path:pathToFile>')
def derivative_video(pathToFile):
    return Response(gen_derivative_frames(pathToFile),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@ app.route('/detection/<path:pathToFile>')
def detection(pathToFile):
    return Response(execute(pathToFile),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@ app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        result = request.form
        email = result["email"]
        password = result["password"]
        try:
            user = auth.sign_in_with_email_and_password(email, password)

            check = str(auth.get_account_info(user['idToken']))
            if ("'emailVerified': True" in check):
                session['user'] = user['idToken']
                return redirect(url_for('index'))
            else:
                return 'Verify your email to login.'

        except:
            dumpSession()
            return redirect(url_for('login'))
    else:
        return render_template('login.html')


@ app.route('/index', methods=['GET', 'POST'])
def index():
    if 'user' in session:
        if request.method == 'POST':
            if request.form['action'] == 'upload':
                file = '-'
                try:
                    f = request.files['file']
                    f.save('static/queries/'+secure_filename(f.filename))
                    file = f.filename
                    return render_template('index.html',
                                           message='success',
                                           filename=file,
                                           home=url_for('index'),
                                           about=url_for('about'))
                except:
                    return render_template('index.html',
                                           message='error',
                                           filename=file,
                                           home=url_for('index'),
                                           about=url_for('about'))
            elif request.form['action'] == 'next':
                file = request.form['filename']
                return redirect(url_for('processing', path=file))
        else:
            return render_template('index.html',
                                   message='',
                                   home=url_for('index'),
                                   about=url_for('about'))
    else:
        return redirect(url_for('login'))


@ app.route('/processing/<path>', methods=['GET', 'POST'])
def processing(path):
    if 'user' in session:
        VideoPath = r'static/queries/'+path
        env = Environment(loader=FileSystemLoader('templates'))
        tmpl = env.get_template('processing.html')
        return Response(tmpl.generate(video_feed=url_for('real_video', pathToFile=VideoPath),
                                      derivative=url_for(
            'derivative_video', pathToFile=VideoPath),
            output=url_for(
            'detection', pathToFile=VideoPath),
            home=url_for('index'),
            about=url_for('about'),
            result=url_for('result')))
    else:
        return redirect(url_for('login'))


@ app.route('/result', methods=['GET', 'POST'])
def result():
    env = Environment(loader=FileSystemLoader('templates'))
    tmpl = env.get_template('result.html')
    return Response(tmpl.generate(table=tableGenertor().to_html(classes='table table-bordered center'),
                                  home=url_for('index'),
                                  about=url_for('about')
                                  ))


@ app.route('/fogot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        result = request.form
        email = result["email"]
        try:
            auth.send_password_reset_email(email)
            return 'Password reset email has been sent! kindly check your email.'
        except:
            return 'no such registered email found!'
    else:
        return render_template('forgot.html')


@ app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        result = request.form  # Get the data submitted
        email = result["email"]
        password = result["password"]
        name = result["name"]
        print(email, password, name)
        try:
            user = auth.create_user_with_email_and_password(email, password)
            auth.send_email_verification(user['idToken'])
            return redirect(url_for('login'))
        except:
            print('error')
            return redirect(url_for('register'))
    else:
        return render_template('register.html')


@ app.route('/reset', methods=['GET', 'POST'])
def reset():
    return render_template('reset.html')


@ app.route('/about')
def about():
    return render_template('about.html',
                           home=url_for('index'),
                           about=url_for('about'))


if __name__ == '__main__':
    # port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port)
    app.run(debug=True)
