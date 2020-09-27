import requests
import os
from google.cloud import firestore
from bs4 import BeautifulSoup as bs
from Bridge import message_validation

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './igneous-trail-290716-59bdaa302fe3.json'
db = firestore.Client()

key = "17c4275203c84fed872772fa17a0e5ea"
url = "https://newsapi.org/v2/top-headlines?country=us&apiKey=" + key

response = requests.get(url).json()

articles_ref = db.collection(u'articles')
for i, article in enumerate(response['articles']):
    url = article['url']
    title = article['title']
    urlToImage = article['urlToImage']

    paragraphs = bs(requests.get(url).text, 'html.parser').find_all('p')

    counts_profanity = 0
    counts_sentiment = 0
    example_fail = ""
    for p in paragraphs:
        try:
            sent_counter = message_validation.analyze_sentiment(p.getText(), True, True, True)
            type = sent_counter['failureType']
            content = sent_counter['content']

            if type == 'sentiment':
                counts_sentiment += 1
                example_fail += content + "%%"
            else:
                counts_profanity += 1

        except:
            pass

    data = {
        'url': url,
        'title': title,
        'urlToImage': urlToImage,
        'countsProfanity': counts_profanity,
        'countsSentiment': counts_sentiment,
        'exampleFail': example_fail[:-2]
    }

    articles_ref.document(u''+str(i)).set(data)
