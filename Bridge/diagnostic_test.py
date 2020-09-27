from google.cloud import language_v1
from google.cloud.language_v1 import enums, types

import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'igneous-trail-290716-a4ac2eb4573a.json'

client = language_v1.LanguageServiceClient()


def get_answer_sentiment(text_content, words_of_interest):
    overall_sentiment_result = analyze_overall_sentiment(text_content)
    word_sentiment_result = sample_analyze_entity_sentiment(text_content, words_of_interest)

    word_sentiment_max_weight = 0.7
    # none of these values should be negative
    word_sentiment_importance = word_sentiment_result[2] / word_sentiment_result[3] * word_sentiment_max_weight
    sentiment_result = overall_sentiment_result[0] * (1 - word_sentiment_importance) + word_sentiment_result[0] * word_sentiment_importance
    return sentiment_result


def analyze_overall_sentiment(text_content):

    # Available types: PLAIN_TEXT, HTML
    type_ = enums.Document.Type.PLAIN_TEXT

    language = "en"
    document = {"content": text_content, "type": type_, "language": language}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = enums.EncodingType.UTF8

    response = client.analyze_sentiment(document, encoding_type=encoding_type)

    # Get overall sentiment of the input document
    overall_sentiment_score = response.document_sentiment.score
    overall_sentiment_magnitude = response.document_sentiment.magnitude

    return (overall_sentiment_score, overall_sentiment_magnitude)


def sample_analyze_entity_sentiment(text_content, words_of_interest):

    # Available types: PLAIN_TEXT, HTML
    type_ = enums.Document.Type.PLAIN_TEXT

    language = "en"
    document = {"content": text_content, "type": type_, "language": language}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = enums.EncodingType.UTF8

    response = client.analyze_entity_sentiment(document, encoding_type=encoding_type)

    if isinstance(words_of_interest, dict):
        # Get overall sentiment of the input document
        overall_word_sentiment_score = 0
        overall_word_sentiment_magnitude = 0

        max_score_sum = 0
        for value in words_of_interest.values():
            max_score_sum = max_score_sum + abs(value)

        relative_score_sum = 0
        for entity in response.entities:
            if entity.name in words_of_interest:
                relative_score_sum = relative_score_sum + abs(words_of_interest[entity.name])

        for entity in response.entities:
            if entity.name in words_of_interest:
                sentiment = entity.sentiment

                overall_word_sentiment_score = overall_word_sentiment_score + (sentiment.score * words_of_interest[entity.name] / relative_score_sum)
                overall_word_sentiment_magnitude = overall_word_sentiment_magnitude + (sentiment.score * words_of_interest[entity.name] / relative_score_sum)

        return (overall_word_sentiment_score, overall_word_sentiment_magnitude, relative_score_sum, max_score_sum)
    elif isinstance(words_of_interest, str):
        for entity in response.entities:
            if entity.name == words_of_interest:
                sentiment = entity.sentiment
                return (sentiment.score, sentiment.magnitude, 1, 1)

        return (0, 0, 0, 1)
    else:
        # Get overall sentiment of the input document
        overall_word_sentiment_score = 0
        overall_word_sentiment_magnitude = 0

        count = 0

        for entity in response.entities:
            if entity.name in words_of_interest:
                sentiment = entity.sentiment
                overall_word_sentiment_score = overall_word_sentiment_score + sentiment.score
                overall_word_sentiment_magnitude = overall_word_sentiment_magnitude + sentiment.magnitude
                count = count + 1

        return (overall_word_sentiment_score/count, overall_word_sentiment_magnitude/count, count, len(words_of_interest))


# test_content = """I love pears but hate onions"""
# print(get_answer_sentiment(test_content, {"onions": 2,"pears": 3}))
