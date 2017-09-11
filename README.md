# s3-log-tracking-lambda
AWS lambda which listens for new S3 objects (zipped log files) and creates analytics events from the contents.

## Requirements

Python 3.6, virtualenv, AWS CLI.

## Deploying

```
aws configure
./deploy.sh
```
