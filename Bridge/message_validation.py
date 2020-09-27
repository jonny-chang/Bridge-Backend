
TOP_THRESHOLD = 0.9
BOTTOM_THRESHOLD = -0.8

import xml.etree.ElementTree as ET

from google.cloud import language_v1
from google.cloud.language_v1 import enums, types

import sys

if sys.version_info < (2, 8):
    try:
        from profanity_check import predict, predict_prob
    except ImportError as err:
        predict = None
        predict_prob = None
        print("Failed AI profanity test import")
else:
    predict = None
    predict_prob = None

import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'igneous-trail-290716-a4ac2eb4573a.json'

client = language_v1.LanguageServiceClient()


def profanity_check(text_content):
    f = open("list.txt", "r").read().splitlines()
    for line in f:
        without_line_breaks = line.replace("\n", " ")
        if (without_line_breaks) in text_content.lower().split(" ") or (without_line_breaks + ".") in text_content.lower().split(" "):
            return (True, line)

    return (False, None)


def profanityAnalysis(text_content):
    start_index = 0
    text_content_arr = text_content.split()
    end_index = len(text_content_arr)

    profanity_baseline = predict_prob([text_content])[0]/(end_index-start_index)

    profanity_split_1 = predict_prob([' '.join(text_content_arr[start_index:min(end_index//2 + 1, end_index - 1)])])[0]/(min(end_index//2 + 1, end_index - 1) - start_index)
    profanity_split_2 = predict_prob([' '.join(text_content_arr[max(1, end_index//2 - 1):end_index])])[0]/(end_index-max(1, end_index//2 - 1))
    while(
        (end_index - start_index) > 1
        and (profanity_baseline <= profanity_split_1 or profanity_baseline <= profanity_split_2)
    ):
        if profanity_split_1>=profanity_split_2:
            profanity_baseline = profanity_split_1
            start_index = start_index
            end_index = min((start_index + end_index) // 2, end_index - 1)
        else:
            profanity_baseline = profanity_split_1
            start_index = max(1,(start_index + end_index) // 2)
            end_index = end_index
        profanity_split_1 = predict_prob(
            [' '.join(text_content_arr[start_index:min((start_index + end_index) // 2, end_index - 1)])])[0]/max(1,(min((start_index + end_index) // 2, end_index - 1) - start_index))
        profanity_split_2 = predict_prob([' '.join(text_content_arr[max(1,(start_index + end_index) // 2):end_index])])[0]/max(1,(end_index-max(1,(start_index + end_index) // 2)))

    return (start_index, end_index)


def analyze_sentiment(text_content, extra_recommendations=False, word_recommendations=False, ai_profanity_detection=False):

    result = {
        'success': True
    }

    profanity_result = profanity_check(text_content)
    if profanity_result[0]:
        result['success'] = False
        result['failureType'] = 'profanity'
        result['beginOffset'] = text_content.lower().find(profanity_result[1])
        result['length'] = len(profanity_result[1])
        result['content'] = profanity_result[1]
        result['message'] = "We have detected that the following profane word, please remove it."
        return result

    if ai_profanity_detection and predict is not None and predict_prob is not None:
        if predict([text_content])[0] == 1:
            result['success'] = False
            result['failureType'] = 'profanity'
            profanity_bounds_tuple = profanityAnalysis(text_content)
            text_content_arr = text_content.split()
            result['beginOffset'] = len(" ".join(text_content_arr[:profanity_bounds_tuple[0]]))
            result['length'] = len(" ".join(text_content_arr[profanity_bounds_tuple[0]:profanity_bounds_tuple[1]]))
            result['content'] = " ".join(text_content_arr[profanity_bounds_tuple[0]:profanity_bounds_tuple[1]])
            result['message'] = "We have detected that the following is profane, please change or remove it."
            return result


    # Available types: PLAIN_TEXT, HTML
    type_ = enums.Document.Type.PLAIN_TEXT

    # Optional. If not specified, the language is automatically detected.
    # https://cloud.google.com/natural-language/docs/languages <-- supported languages
    language = "en"

    document = {"content": text_content, "type": type_, "language": language}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = enums.EncodingType.UTF8

    sentiment_response = client.analyze_sentiment(document, encoding_type=encoding_type)

    for sentence in sentiment_response.sentences:
        if sentence.sentiment.score < BOTTOM_THRESHOLD or sentence.sentiment.score > TOP_THRESHOLD:

            document = {"content": sentence.text.content, "type": type_, "language": language}
            entity_sentiment_response = client.analyze_entity_sentiment(document, encoding_type=encoding_type)

            if extra_recommendations:
                extreme_entity = None
                extreme_entity_score = 0.4 if sentence.sentiment.score > 0 else -0.4
                for entity in entity_sentiment_response.entities:
                    entity_sentiment = entity.sentiment
                    if sentence.sentiment.score > 0 and entity_sentiment.score > extreme_entity_score:
                        extreme_entity = entity.name
                        extreme_entity_score = entity_sentiment.score
                    elif sentence.sentiment.score < 0 and entity_sentiment.score < extreme_entity_score:
                        extreme_entity = entity.name
                        extreme_entity_score = entity_sentiment.score
                if extreme_entity is not None:
                    if sentence.sentiment.score < BOTTOM_THRESHOLD:
                        result['recommendation'] = "Your mention of " + extreme_entity + " is particularly negative"
                    elif sentence.sentiment.score > TOP_THRESHOLD:
                        result['recommendation'] = "Your mention of " + extreme_entity + " is particularly positive"

            if word_recommendations:
                root = ET.parse('sentiments.xml').getroot()

                max_sum = 0
                word_of_interest = None
                for index, word in enumerate(sentence.text.content.split()):
                    xml_objects = root.findall("./word[@form='" + word + "']")

                    sum = 0
                    for xml_object in xml_objects:
                        if ('polarity' in xml_object.attrib) and ('subjectivity' in xml_object.attrib):
                            sum = sum + abs(float(xml_object.attrib['polarity'])) + abs(float(xml_object.attrib['subjectivity']))
                    if sum > max_sum:
                        max_sum = sum
                        word_of_interest = word
                if word_of_interest is not None:
                    result['wordChange'] = "We recommend that you change the word " + word_of_interest + "."
                    result['wordChangeStart'] = sentence.text.begin_offset + sentence.text.content.find(word_of_interest)

            result['success'] = False
            result['failureType'] = 'sentiment'
            result['beginOffset'] = sentence.text.begin_offset
            result['length'] = len(sentence.text.content)
            result['content'] = sentence.text.content
            if sentence.sentiment.score < BOTTOM_THRESHOLD:
                result['message'] = "This sentence has a strong negative sentiment try to make it more neutral."
            elif sentence.sentiment.score > TOP_THRESHOLD:
                result['message'] = "This sentence has a strong positive sentiment try to make it more neutral."
            return result

    return result

# test_content = """I am thinking a lot right now sir. You are a stupid person"""
# print(analyze_sentiment(test_content, extra_recommendations=True, word_recommendations=True))
