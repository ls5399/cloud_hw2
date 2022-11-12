import json
import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
# import requests
import urllib.parse
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

headers = { "Content-Type": "application/json" }
region = 'us-east-1'
b2_bucket_name = "f2022-assignment2-b2"
lex = boto3.client('lex-runtime', region_name=region)

def push_to_lex(query):
    lex = boto3.client('lex-runtime')
    print("lex client initialized")
    print(query);
    response = lex.post_text(
        botName='SearchPhotoBot',
        botAlias='searchphoto',
        userId="id",
        inputText=query
    )
    print("test changes new")
    print("lex-response", response)
    labels = []
    if 'slots' not in response:
        print("No photo collection for query {}".format(query))
    else:
        print("slot: ", response['slots'])
        slot_val = response['slots']
        for key, value in slot_val.items():
            if value != None:
                labels.append(value)
    return labels


# Function to establish OpenSearch connection
def connect_openSearch(host, username, password):
    os = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=(username, password),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    return os


def get_photo_path_by_search_os(keys):
    os_doamin = "search-photos-holqwqitjqfgxfgpqsnp5e25wu.us-east-1.es.amazonaws.com"

    os = connect_openSearch(os_doamin, "huiminzhang", "F2022CC_102s@Apass")

    resp = []
    for key in keys:
        if (key is not None) and key != '':
            searchData = os.search({"query": {"match": {"labels": key}}})
            resp.append(searchData)
    print(resp)
    output = set()
    for r in resp:
        if 'hits' in r:
            for val in r['hits']['hits']:
                key = val['_source']['objectKey']
                if key not in output:
                    output.add('https://s3.amazonaws.com/' + b2_bucket_name + '/' + key)
    print(output)
    return list(output)


def lambda_handler(event, context):
    # TODO implement
    print(event)
    q = event['queryStringParameters']['q']
    # q = "show me cat" 
    logger.debug(f"query: {q}")
    labels = push_to_lex(q)
    print("labels", labels)
    if len(labels) != 0:
        img_paths = get_photo_path_by_search_os(labels)
    logger.debug(f"Image paths: {img_paths}")
    if not img_paths:
        return {
            'statusCode': 404,
            'headers': {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*"},
            'body': json.dumps('No Results found')
        }
    else:
        print(img_paths)
        return {
            'statusCode': 200,
            'headers': {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*"},
            'body': json.dumps(img_paths)
        }
