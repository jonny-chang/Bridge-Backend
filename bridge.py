import os
import time
from google.cloud import firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from Bridge import diagnostic_test, message_validation
import random
import string
import json
import requests

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


@app.route("/get-questions", methods=["GET"])
def get_questions():
    all_questions = {}
    try:
        questions_ref = db.collection(u'questions').stream()

        for doc in questions_ref:
            question_dict = doc.to_dict()
            all_questions[str(doc.id)] = {'status': 1, 'question': question_dict['question'], 'category': question_dict['category'], 'message': 'Success.'}

        return all_questions

    except:
        return {"status": 0, 'question': '', 'category': '', 'message': 'Something went wrong. Please try again later.'}

    
@app.route("/get-articles", methods=["GET"])
def get_articles():
    all_articles = {}
    try:
        articles_ref = db.collection(u'articles').stream()
        
        articles_arr = []
        for doc in articles_ref:
            article_dict = doc.to_dict()
            articles_arr.append(article_dict)

        return jsonify(articles_arr)

    except:
        return {"status": 0, 'message': 'Something went wrong. Please try again later.'}    
    

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
            print(other_sent)

            return {'status': 1, 'message': 'Success!'}

        else:
            sent = float(request.args['sent_score'])
            update_sent(question['category'], sent, email)

            return {'status': 1, 'message': 'Success!'}

    except:
        return {'status': 0, 'message': 'An error occured. Please try again later.'}


@app.route('/generate-chat-token', methods=['GET'])
def generate_chat_token():
    email = request.args['email']

    chat_state = db.collection(u'chat-token').document(u'state')
    chat_state_dict = chat_state.get().to_dict()

    user_info = db.collection(u'users').document(u'' + email).get().to_dict()
    domestic = user_info['domestic']
    economic = user_info['economic']
    electoral = user_info['electoral']
    environmental = user_info['environmental']
    foreign = user_info['foreign']
    health = user_info['health']
    immigration = user_info['immigration']
    social = user_info['social']

    try:
        if chat_state_dict['in_chat'] < 2:
            chat_state_dict['in_chat'] += 1
            chat_state.set(chat_state_dict)
            return {
                'status': 1,
                'num_ppl': chat_state_dict['in_chat'],
                'token': chat_state_dict['token'],
                'email': email,
                'domestic_policy': domestic,
                'economic': economic,
                'electoral': electoral,
                'environmental': environmental,
                'foreign_policy': foreign,
                'health': health,
                'immigration': immigration,
                'social': social
            }

        else:
            new_token = ''.join(random.choice(string.ascii_letters) for i in range(10))
            print(new_token)
            chat_state_dict['in_chat'] = 1
            chat_state_dict['token'] = new_token
            chat_state.set(chat_state_dict)

            return {
                'status': 1,
                'num_ppl': chat_state_dict['in_chat'],
                'token': new_token,
                'email': email,
                'domestic_policy': domestic,
                'economic': economic,
                'electoral': electoral,
                'environmental': environmental,
                'foreign_policy': foreign,
                'health': health,
                'immigration': immigration,
                'social': social
            }
    except:
        return {
            'status': 0,
            'message': 'Something went wrong. Please try again later.'
        }


@app.route("/create-conversation", methods=["GET"])
def create_conversation():
    user1 = request.args['user1']
    user2 = request.args['user2']
    most_different = request.args['different_subject']
    most_similar = request.args['similar_subject']
    conversation_id = request.args['conversation_id']
    welcome_message = "Welcome to the chat! We hope you have a nice and educational discussion."
    if most_similar and most_different:
        welcome_message = "The topic you two have most differences in is: " + most_different + " and the topic you two agree on the most is: " + most_similar

    app_id = "tvziCsZk"

    url = "https://api.talkjs.com/v1/" + app_id + "/conversations/" + conversation_id

    payload = "{\r\n    \"participants\": [\"" + str(user1) + "\", \"" + str(user2) +"\"],\r\n    \"subject\": \"Chat Room\",\r\n    \"welcomeMessages\": [\"" + welcome_message + "\"],\r\n    \"custom\": {\r\n        \"productId\": \"454545\"\r\n    }\r\n}"
    headers = {
        'Authorization': 'Bearer sk_test_Gg6riEPhRKUGhAluYSrVOyAA',
        'Content-Type': 'application/json',
        'Cookie': '__cfduid=d74cbb38aec0cd4148552f4703bc033ab1601210721'
    }

    response = requests.request("PUT", url, headers=headers, data=payload)

    if response.status_code:
        return {'status': 1, 'code': response.status_code, 'conversation_id': conversation_id}
    else:
        return {'status': 0, 'code': 'Error', 'conversation_id': conversation_id}    


@app.route("/send-message", methods=["GET"])
def send_message():
    message = request.args['message']
    user = request.args['user']
    conversation_id = request.args['conversation_id']

    app_id = "tvziCsZk"
    url = "https://api.talkjs.com/v1/" + app_id + "/conversations/" + conversation_id + "/messages"

    sent_result = message_validation.analyze_sentiment(message, True, True, True)

    if sent_result['success']:
        payload = "[{\"text\": \"" + message + "\", \"sender\": \"" + user + "\", \"type\": \"UserMessage\"}]"
        headers = {
            'Authorization': 'Bearer sk_test_Gg6riEPhRKUGhAluYSrVOyAA',
            'Content-Type': 'application/json',
            'Cookie': '__cfduid=d74cbb38aec0cd4148552f4703bc033ab1601210721'
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        return {"status": 1, "code": response.status_code}

    else:
        return {"status": 0, "code": sent_result}


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
    app.run(host="0.0.0.0", port=80, debug=True)
