# 
# Copyright 2015 Ryan Holland
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an 
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and limitations under the License.
#

import boto3, botocore

## Set the values below if using Lambda Scheduled Event as an Event Source, otherwise leave empty and send data through the Lambda event payload
S3BCUKET=''
S3PREFIX=''
RDSINSANCE=''
LOGNAME=''
LASTRECIEVED=''
REGION=''

def lambda_handler(event, context):
	firstRun = False
	logFileData = ""
	if {'BucketName','S3BucketPrefix','RDSInstanceName','LogNamePrefix','lastRecievedFile','Region'}.issubset(event):
		S3BucketName = event['BucketName']	
		S3BucketPrefix = event['S3BucketPrefix']
		RDSInstanceName = event['RDSInstanceName']
		logNamePrefix = event['LogNamePrefix']
		lastRecievedFile = S3BucketPrefix + event['lastRecievedFile']
		region = event['Region']
	else:
		S3BucketName = S3BCUKET
		S3BucketPrefix = S3PREFIX
		RDSInstanceName = RDSINSANCE
		logNamePrefix = LOGNAME
		lastRecievedFile = S3BucketPrefix + LASTRECIEVED
		region = REGION
	RDSclient = boto3.client('rds',region_name=region)
	S3client = boto3.client('s3',region_name=region)
	dbLogs = RDSclient.describe_db_log_files( DBInstanceIdentifier=RDSInstanceName, FilenameContains=logNamePrefix)
	lastWrittenTime = 0
	lastWrittenThisRun = 0
	try:
		S3response = S3client.head_bucket(Bucket=S3BucketName)
	except botocore.exceptions.ClientError as e:
		error_code = int(e.response['ResponseMetadata']['HTTPStatusCode'])
		if error_code == 404:
			return "Error: Bucket name provided not found"
		else:
			return "Error: Unable to access bucket name, error: " + e.response['Error']['Message']
	try:
		S3response = S3client.get_object(Bucket=S3BucketName, Key=lastRecievedFile)
	except botocore.exceptions.ClientError as e:
		error_code = int(e.response['ResponseMetadata']['HTTPStatusCode'])
		if error_code == 404:
			print("It appears this is the first log import, all files will be retrieved from RDS")
			firstRun = True
		else:
			return "Error: Unable to access lastRecievedFile name, error: " + e.response['Error']['Message']
	
	if firstRun == False:
		lastWrittenTime = int(S3response['Body'].read(S3response['ContentLength']))
		print("Found marker from last log download, retrieving log files with lastWritten time after %s" % str(lastWrittenTime))
	for dbLog in dbLogs['DescribeDBLogFiles']:
		if ( int(dbLog['LastWritten']) > lastWrittenTime ) or firstRun:
			print("Downloading log file: %s found and with LastWritten value of: %s " % (dbLog['LogFileName'],dbLog['LastWritten']))
			if int(dbLog['LastWritten']) > lastWrittenThisRun:
				lastWrittenThisRun = int(dbLog['LastWritten'])
			logFile = RDSclient.download_db_log_file_portion(DBInstanceIdentifier=RDSInstanceName, LogFileName=dbLog['LogFileName'],Marker='0')
			logFileData = logFile['LogFileData']
			while logFile['AdditionalDataPending']:
				logFile = RDSclient.download_db_log_file_portion(DBInstanceIdentifier=RDSInstanceName, LogFileName=dbLog['LogFileName'],Marker=logFile['Marker'])
				logFileData += logFile['LogFileData']
			byteData = str.encode(logFileData)
			try:
				objectName = S3BucketPrefix + dbLog['LogFileName']
				S3response = S3client.put_object(Bucket=S3BucketName, Key=objectName,Body=byteData)
			except botocore.exceptions.ClientError as e:
				return "Error writting object to S3 bucket, S3 ClientError: " + e.response['Error']['Message']
			print("Writting log file %s to S3 bucket %s" % (objectName,S3BucketName))
	try:
		S3response = S3client.put_object(Bucket=S3BucketName, Key=lastRecievedFile, Body=str.encode(str(lastWrittenThisRun)))			
	except botocore.exceptions.ClientError as e:
		return "Error writting object to S3 bucket, S3 ClientError: " + e.response['Error']['Message']
	print("Wrote new Last Written Marker to %s in Bucket %s" % (lastRecievedFile,S3BucketName))
	return "Log file export complete"










