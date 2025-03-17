"""app.py"""
import os
import json
import requests
import redis
import json
import shutil
from datetime import datetime
from pymongo import MongoClient
from elasticsearch import Elasticsearch

MONGODB_URI = os.getenv('MONGODB_URI')
ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL')
REDIS_URL = os.getenv('REDIS_URL')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def delete_data(doc_id, file_path):
    """
    Mark a file on disk with 'deleted_' prefix and delete corresponding data in MongoDB, Elasticsearch, and Redis.

    Parameters:
    - doc_id (str): The document ID or unique identifier for the data.
    - file_path (str): The path to the file on disk associated with the data.

    This function does not physically delete the file but renames it to indicate deletion.
    """
    # Mark File on Disk
    base_path, filename = os.path.split(file_path)
    new_filename = f"deleted_{filename}"
    new_file_path = os.path.join(base_path, new_filename)
    shutil.move(file_path, new_file_path)
    print(f"File marked as deleted: {new_file_path}")

    # Delete from MongoDB
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client['your_database_name']  # Replace with your actual database name
    collection = db['data']
    mongo_result = collection.delete_one({'_id': doc_id})
    print(f"MongoDB document deleted: {mongo_result.deleted_count}")

    # Delete from Elasticsearch
    es = Elasticsearch([ELASTICSEARCH_URL])
    es_result = es.delete(index='data_search', id=doc_id, ignore=[404])
    print(f"Elasticsearch document deleted: {es_result}")

    # Delete from Redis Cache
    r = redis.Redis.from_url(REDIS_URL)
    cache_key = f"datacache_{doc_id}"
    r.delete(cache_key)
    print(f"Redis cache entry deleted for key: {cache_key}")

def update_data(doc_id, updated_data):
    """
    Update a document in MongoDB, Elasticsearch, and Redis.

    Parameters:
    - doc_id (str): The document ID or unique identifier for the data.
    - updated_data (dict): The updated data for the document.

    This function updates the document with the given `doc_id` in MongoDB and Elasticsearch,
    and updates the cached version in Redis if it exists.
    """
    # Update MongoDB
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client['your_database_name']  # Replace with your actual database name
    collection = db['data']
    mongo_result = collection.update_one({'_id': doc_id}, {'$set': updated_data})
    print(f"MongoDB updated: {mongo_result.modified_count} document(s)")

    # Update Elasticsearch
    es = Elasticsearch([ELASTICSEARCH_URL])
    es_result = es.update(index='data_search', id=doc_id, body={'doc': updated_data})
    print(f"Elasticsearch updated: {es_result['_id']}")

    # Update Redis Cache if exists
    r = redis.Redis.from_url(REDIS_URL)
    cache_key = f"datacache_{doc_id}"
    if r.exists(cache_key):
        r.set(cache_key, json.dumps(updated_data))
        print(f"Redis cache updated for key: {cache_key}")
    else:
        print("No Redis cache entry to update.")

def read_from_cache_or_db(doc_id):
    """
    Attempt to read data from Redis cache, falling back to MongoDB if not found.

    Parameters:
    - doc_id (str): The document ID or unique identifier for the data.

    Returns:
    - The data as a dictionary.
    """
    # Connect to Redis
    r = redis.Redis.from_url(REDIS_URL)
    cache_key = f"datacache_{doc_id}"

    # Try to get the data from Redis cache
    cached_data = r.get(cache_key)
    if cached_data:
        print("Data retrieved from Redis cache.")
        return json.loads(cached_data)

    # If not in cache, fall back to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client['your_database_name']  # Replace with your actual database name
    collection = db['data']

    # Query MongoDB using the document ID
    data = collection.find_one({"_id": doc_id})
    if data:
        print("Data retrieved from MongoDB.")
        # Consider updating the cache with this data
        r.set(cache_key, json.dumps(data))
        return data

    # If the data is not found in both Redis and MongoDB
    print("Data not found.")
    return None

def write_to_disk(data):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"filebu_{timestamp}.json"
    with open(filename, 'w') as file:
        json.dump(data, file)
    return filename

def write_to_mongodb(data):
    client = MongoClient(MONGODB_URI)
    db = client['your_database_name']  # Replace with your database name
    collection = db['data']
    result = collection.insert_one(data)
    return result.inserted_id

def write_to_elasticsearch(data, doc_id):
    es = Elasticsearch([ELASTICSEARCH_URL])
    response = es.index(index="data_search", id=doc_id, body=data)
    return response

def post_to_webhook(data):
    webhook_url = WEBHOOK_URL
    response = requests.post(webhook_url, json=data)
    return response.status_code

def process_data(data):
    # Step 1: Write to disk
    filename = write_to_disk(data)
    print(f"Data written to disk: {filename}")

    # Step 2: Write to MongoDB
    doc_id = write_to_mongodb(data)
    print(f"Data written to MongoDB with ID: {doc_id}")

    # Step 3: Write to Elasticsearch
    es_response = write_to_elasticsearch(data, doc_id)
    print(f"Data indexed in Elasticsearch with ID: {es_response['_id']}")

    # Step 4: Write to Redis
    write_to_redis(data, doc_id)
    print(f"Data cached in Redis with key: datacache_{doc_id}")

    # Step 5: Post to Webhook
    status_code = post_to_webhook(data)
    print(f"Data posted to webhook with status code: {status_code}")

# Example data
data = {"name": "John Doe", "age": 30}
process_data(data)
# Example usage
doc_id = 'your_document_id_here'
file_path = '/path/to/your/file.txt'  # Replace with the actual file path
delete_data(doc_id, file_path)
# Example usage
doc_id = 'your_document_id_here'
data = read_from_cache_or_db(doc_id)
print(data)
# Example usage
doc_id = 'your_document_id_here'
updated_data = {'field_to_update': 'new_value'}
update_data(doc_id, updated_data)