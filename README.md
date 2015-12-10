## AWS Lambda function to export Amazon RDS MySQL Query Logs to S3

### Requirments
In order to enable query logging in RDS you must enable the general_log in the RDS Parameter Group with the output format to FILE
Details on how to do this are available from the Amazon RDS documentation 
http://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_LogAccess.Concepts.MySQL.html 

### Creating the IAM Execution Role

The AWS Lambda service uses an IAM role to execute the function, below is the IAM policy needed by the function to run.  
*Replace [BucketName] below with the name of the bucket in your account where you want the log files to be written to*
```{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::[BucketName]s/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::[BucketName]"
            ]
        },
        {
            
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBLogFiles",
                "rds:DownloadDBLogFilePortion"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}```

### Configuring the AWS Lambda fucntion
To create the new AWS Lambda function either paste the contents of the rds_mysql_to_s3.py file in the in-line code editor or create a zip file that contains only the rds_mysql_to_s3.py and upload the zip file.

The Lambda Handler needs to be set to: rds_mysql_to_s3.lambda_handler
The Runtime Environment is Python 2.7
Role needs to be set to a role that has the policy above.
Modify the Timeout value (under Advanced) from the default of 3 seconds to at least 1 minute, if you have very large log files you may need to increase the timeout even further.

### Creating a Test Event
The event input for the function is a JSON package that contains the information about the RDS instance and S3 bucket and has the following values:
```{
  "BucketName": "[BucketName]",
  "RDSInstanceName": "[RDS DB Instance Name]",
  "S3BucketPrefix": "[Prefix to use within the specified bucket]/",
  "LogNamePrefix" : "general/mysql-general",
  "lastRecievedFile" : "lastWrittenMarker",
  "Region"  :"[RegionName]"
}```

### Scheduling the AWS Lambda Function
Since RDS only maintains log files for a maximum of 24 hours or until the log data exceeds 2% of the storage allocated to the DB Instance its adviseable to have the function run at least once per day.  By setting up an Event Source in Lambda you can have the function run on a scheduled basis.  As new log files are retrieved from the RDS service they will overwrite older log files of the same name in the S3 bucket/prefix so you should retrieve the log files from S3 prior to subsequent runs of the function.

