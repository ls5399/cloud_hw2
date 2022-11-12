import json
import os
import time
import logging
import boto3
from datetime import datetime

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
port = 443

awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

rekognition = boto3.client('rekognition')



def rekognition_function(bucket_name, file_name):
    
    client = boto3.client('rekognition')
    response = client.detect_labels(
        Image={
            'S3Object':{
                'Bucket':bucket_name, 
                'Name': file_name
            }
        }, 
        MaxLabels=10 
    )
    
    label_names = []

    label_names = list(map(lambda x:x['Name'], response['Labels']))
    label_names = [x.lower() for x in label_names]
    print("label names are: ", label_names)
    return label_names


# Function to establish OpenSearch connection
def connect_openSearch(host, username, password):
    os = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_auth=(username, password),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    return os

def create_index(os):
    index_name = "photos"
    index_body = {
        'settings': {
            'index': {
                'number_of_shards': 4
            }
        }
    }
    os.indices.create(index_name, body=index_body)
    
def lambda_handler(event, context):
    logger.debug("-- TRIGGER EVENT SUCCESS --")

    logger.debug(credentials)
    records = event['Records']
    os_doamin = "search-photos-holqwqitjqfgxfgpqsnp5e25wu.us-east-1.es.amazonaws.com"
    os = connect_openSearch(os_doamin, "huiminzhang", "F2022CC_102s@Apass")
    
    # This method only runs once in order to create the "photos" index
    # create_index(os);
    
    s3 = boto3.client('s3')
    for record in records:

        s3object = record['s3']
        bucket = s3object['bucket']['name']
        objectKey = s3object['object']['key']
        
        response = s3.head_object(Bucket=bucket, Key=objectKey)
        logger.debug(f"Head object are: {response}")
        if response["Metadata"]:
            customlabels = response["Metadata"]["customlabels"]
            logger.debug(f"Customlabels are: {customlabels}")
            customlabels = customlabels.split(',')
            customlabels = list(map(lambda x: x.lower(), customlabels))
        timestamp = record['eventTime']
    
        image = {
            'S3Object' : {
                'Bucket' : bucket,
                'Name' : objectKey
            }
        }

        rekresponse = rekognition.detect_labels(Image = image)
        labels = list(map(lambda x : x['Name'], rekresponse['Labels']))
        labels = [x.lower() for x in labels]
        
        if response["Metadata"]:
            for cl in customlabels:
                print(cl)
                cl = cl.lower().strip()
                if cl not in labels:
                    labels.append(cl)

        esObject = json.dumps({
            'objectKey' : objectKey,
            'bucket' : bucket,
            'createdTimesatamp' : timestamp,
            'labels' : labels
        })
        os.index(index = "photos", id = objectKey, body = esObject, refresh = True)
    
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
