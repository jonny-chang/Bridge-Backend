import os
import time
from google.cloud import firestore
from flask import Flask, request
from flask_cors import CORS
from datetime import datetime, timedelta
from Bridge import diagnostic_test

app = Flask(__name__)
CORS(app)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './igneous-trail-290716-59bdaa302fe3.json'
db = firestore.Client()


@app.route("/verify-login", methods=["GET"])
def verify_login():
    users_ref = db.collection(u'users')
    email = request.args['email']
    pwd = request.args['pwd']

    d = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    d = time.strptime(d, "%Y-%m-%d %H:%M:%S")
    exp = int(time.mktime(d))

    return_statement = "This user does not exist."
    user = users_ref.document(u''+email).get()

    if user.exists:
        user_dict = user.to_dict()
        return_statement = "The password entered is not correct."
        print(user_dict['password'])
        if user_dict['password'] == pwd:
            return {'email': email, 'pwd': pwd, 'status': 1, 'message': 'Successful Login', 'expire': exp}
        else:
            return {'email': email, 'pwd': pwd, 'status': 0, 'message': return_statement, 'expire': exp}

    return {'email': email, 'pwd': pwd, 'status': 0, 'message': return_statement, 'expire': exp}


@app.route("/register-user", methods=["GET"])
def register_user():
    users_ref = db.collection(u'users')
    email = request.args['email']

    data = {
        u'password': request.args['pwd'],
        u'fname': request.args['fname'],
        u'lname': request.args['lname']
    }

    try:
        user = users_ref.document(u''+email).get()
        if user.exists:
            return {'status': 0, 'message': 'That email is already registered in our database.'}

        password_stat, message = check_password(request.args['pwd'])
        if not password_stat:
            return {'status': 0, 'message': message}

        users_ref.document(u''+email).set(data)
        return {'status': 1, 'message': 'User successfully registered.'}

    except:
        return {'status': 0, 'message': 'Something went wrong. Please try again later.'}


@app.route("/delete-user", methods=["GET"])
def delete_user():
    try:
        users_ref = db.collection(u'users')
        user = users_ref.document(u'' + request.args['email']).get()
        if not user.exists:
            return {'status': 0}

        users_ref.document(u''+request.args['email']).delete()
        return {"status": 1}
    except:
        return {"status": 0}


@app.route("/get-question", methods=["GET"])
def get_question():
    question_id = request.args['id']

    try:
        questions_ref = db.collection(u'questions')
        question = questions_ref.document(u'' + request.args['id']).get()
        if not question.exists:
            return {'status': 0, 'question': '', 'category': '', 'message': 'Question does not exist.'}

        question_dict = question.to_dict()
        return {'status': 1, 'question': question_dict['question'], 'category': question_dict['category'], 'message': 'Success.'}

    except:
        return {"status": 0, 'question': '', 'category': '', 'message': 'Something went wrong. Please try again later.'}


@app.route("/process-answer-sentiment", methods=["GET"])
def analyze_answer_sentiment():
    used_other = request.args['used_other']
    id = request.args['id']
    email = request.args['email']
    question = db.collection(u'questions').document(u'' + str(id)).get().to_dict()

    try:
        if used_other:
            other_text = request.args['other_text']

            keywords = question['keywords'].split()
            weights = [float(x) for x in question['weights'].split()]

            keyword_dict = {}

            for i in range(0, len(keywords)):
                keyword_dict[keywords[i]] = weights[i]

            other_sent = diagnostic_test.get_answer_sentiment(other_text, keyword_dict)
            update_sent(question['category'], other_sent, email)

            return {'status': 1, 'message': 'Success!'}

        else:
            sent = request.args['sent_score']
            update_sent(question['category'], sent, email)

            return {'status': 1, 'message': 'Success!'}

    except:
        return {'status': 0, 'message': 'An error occured. Please try again later.'}


def check_password(password):
    if len(password) < 6:
        return False, "Password must be 6 characters or longer."

    return True, ""


def update_sent(category, sentiment, email):
    user = db.collection(u'users').document(u''+email)
    user_dict = user.get().to_dict()

    if category in user_dict:
        curr_sent = user_dict[category]
        user_dict[category] = curr_sent*0.7 + sentiment*0.3

        user.set(user_dict)

    else:
        user_dict[category] = sentiment
        user.set(user_dict)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
