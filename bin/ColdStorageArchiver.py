import sys
import boto3
import json
import os
import base64
import time
from botocore.exceptions import ClientError

import splunk.conf_util

SPLUNK_HOME_PATH = os.environ.get('SPLUNK_HOME', '/opt/splunk')
DATA_ARCHIVE_CONF_PATH = os.path.join(SPLUNK_HOME_PATH, 'etc', 'slave-apps', '_cluster_admin', 'local', 'data_archive.conf')
# todo confirm this is name cworks will use in conf
ARCHIVAL_BUCKET_OPTION_NAME = 'archive'

if __name__ == "__main__":
    # check parameters
    if len(sys.argv) < 14:
        sys.exit('missing arguments')

    #required params
    arg_index_name   = sys.argv[1]
    arg_bucket_path  = sys.argv[2]
    arg_remote_path  = sys.argv[3]
    arg_bucket_id    = sys.argv[4]
    arg_bucket_size  = sys.argv[5]
    arg_start_time   = sys.argv[6]
    arg_end_time     = sys.argv[7]
    arg_bucket_name  = sys.argv[8]
    arg_receipt_path = sys.argv[9]

    arg_access_key   = sys.argv[10]
    arg_secret_key   = sys.argv[11]
    arg_region       = sys.argv[12]
    arg_table_name   = sys.argv[13]
    """
    The following flag is not currently used, but may need to be used in the future if new
    changes to the DDAA feature require unique support in the AWS gov cloud or other 
    FIPS cloud-like environments. See SPL-168479
    """
    is_on_gov_cloud = arg_region.startswith('us-gov')

    if not os.path.exists(DATA_ARCHIVE_CONF_PATH):
        sys.exit('data_archive.conf not found at required path=' + DATA_ARCHIVE_CONF_PATH)

    archival_bucket_name = splunk.conf_util.ConfigMap(DATA_ARCHIVE_CONF_PATH)['buckets'][ARCHIVAL_BUCKET_OPTION_NAME] 


    # get file list and encryption info from receipt.json
    if not os.path.exists(arg_receipt_path):
        sys.exit('failed to locate updated receipt.json: BucketId=' + arg_bucket_id)

    fileList = ''
    cipher_blob = ''
    guid_context = ''
    rawSize = ''
    try:
        with open(arg_receipt_path) as json_data:
            data = json.load(json_data)
            fileList = data["objects"]
            cipher_blob = data["user_data"]["cipher_blob"]
            guid_context = data["user_data"]["uploader_guid"]
            rawSize = data["manifest"]["raw_size"]
    except Exception as exc:
        sys.exit('failed to get info from receipt.json: BucketId=' + arg_bucket_id + '; exception =' + str(exc))

    plaintext = ''
    try:
        kms_client = boto3.client('kms', arg_region)
        kms_response = kms_client.decrypt(CiphertextBlob=b"%s" % base64.b64decode(cipher_blob),EncryptionContext={'guid': guid_context},)
        plaintext = kms_response["Plaintext"]
    except Exception as exc:
        sys.exit('failed to get customer key from receipt.json: BucketId=' + arg_bucket_id + '; exception =' + str(exc))

    # copy data files in the bucket to staging folder, skip receipt.json
    client = boto3.client('s3',
                      #aws_access_key_id = arg_access_key,
                      #aws_secret_access_key = arg_secret_key,
                      region_name = arg_region,
                      )
    old_prefix = arg_remote_path
    new_prefix = ''
    try:
        s = old_prefix.split('/', 1)
        new_prefix = s[0] + '/'  + s[1]
    except Exception as exc:
        sys.exit('failed to get staging path from bucket path: ' + arg_remote_path + '; exception =' + str(exc))

    try:
        for file in fileList:
            if file['size'] == 0:
                continue
            cur_file = file['name'][1:]
            cur_key = old_prefix + cur_file
            old_source = { 'Bucket': arg_bucket_name, 'Key': cur_key}
            new_key = new_prefix + cur_file
            extra_args = {
                'CopySourceSSECustomerAlgorithm' : 'AES256',
                'CopySourceSSECustomerKey' :  plaintext,
                'SSECustomerAlgorithm' : 'AES256',
                'SSECustomerKey' : plaintext,
                }
            response = client.copy(old_source, archival_bucket_name, new_key, ExtraArgs=extra_args)
    except ClientError as err:
        sys.exit('failed to copy bucket to archival bucket: BucketId=' + arg_bucket_id + '; error=' + err.response['Error']['Message'])
    except Exception as exc:
        sys.exit('failed to copy bucket to archival bucket: BucketId=' + arg_bucket_id + '; exception =' + str(exc))
    else:
        sys.stdout.write('successfully copied bucket to archival bucket; ')

    # upload receipt.json with restore flag
    try:
        receipt_key = new_prefix + '/receipt.json'
        data = open(arg_receipt_path, 'rb')
        client.put_object(Key=receipt_key, Bucket=archival_bucket_name, Body=data)
    except ClientError as err:
        sys.exit('failed to copy updated receipt.json to archival bucket: BucketId=' + arg_bucket_id + '; error=' + err.response['Error']['Message'])
    except Exception as exc:
        sys.exit('failed to copy updated receipt.json to archival bucket: BucketId=' + arg_bucket_id + '; exception =' + str(exc))
    else:
        sys.stdout.write('successfully uploaded receipt.json to archival bucket; ')


    # write bucket info to dynamodb
    dynamodb = boto3.resource('dynamodb',
                          region_name = arg_region,
                          #aws_access_key_id= arg_access_key,
                          #aws_secret_access_key= arg_secret_key,
                          )
    try:
        table = dynamodb.Table(arg_table_name)
    except Exception as exc:
        sys.exit('failed to get DynamoDB table: ' + arg_table_name + '; exception =' + str(exc))

    cur_time = str(int(time.time())).zfill(10)
    start_time = arg_start_time.zfill(10)
    try:
        response = table.put_item(Item={
                                  'IndexName' : arg_index_name,
                                  'BucketPath': arg_bucket_path,
                                  'RemoteBucketPath': arg_remote_path,
                                  'BucketId'  : arg_bucket_id,
                                  'StartTime' : int(arg_start_time),
                                  'EndTime'   : int(arg_end_time),
                                  'BucketSize': int(arg_bucket_size),
                                  'FileList'  : json.dumps(fileList),
                                  'RawSize'   : int(rawSize),
                                  'ArchiveTimeWithBucketID': cur_time + "_" + arg_bucket_id,
                                  'StartTimeWithBucketID': start_time + "_" + arg_bucket_id,
                                  'BucketTimeSpan': int(arg_end_time) - int(arg_start_time)
                                  })
    except ClientError as err:
        sys.exit('failed to write bucket info to bucket history table: BucketId=' + arg_bucket_id + '; error=' + err.response['Error']['Message'])
    except Exception as exc:
        sys.exit('failed to write bucket info to bucket history table: BucketId=' + arg_bucket_id + '; exception =' + str(exc))
    else:
        sys.stdout.write('successfully wrote bucket info to bucket history table')
