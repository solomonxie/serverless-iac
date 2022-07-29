#!/usr/bin/env python3
"""
Provides a simple Python wrapper for invoking an API Gateway endpoint using IAM signed requests.
REF: https://gist.github.com/Riebart/dd68c852ca7fbaccaf3bdac4919f351f
Adapted from:
  https://github.com/jmenga/requests-aws-sign/blob/master/requests_aws_sign/requests_aws_sign.py
Example:
    $ python3 apigateway-invoke.py GET https://xxx.execute-api.us-east-1.amazonaws.com/Stage/Method
"""

import os
import re
import sys

import requests
from boto3 import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from urllib.parse import urlparse, urlencode, parse_qs

AWS_IAM_PROFILE_NAME = os.environ.get('AWS_IAM_PROFILE_NAME')
session = Session(profile_name=AWS_IAM_PROFILE_NAME)


def get_signature_headers(method, url_string, body):
    region = re.search("execute-api.(.*).amazonaws.com", url_string).group(1)
    url = urlparse(url_string)
    path = url.path or '/'
    querystring = ''
    if url.query:
        querystring = '?' + urlencode(parse_qs(url.query, keep_blank_values=True), doseq=True)
    safe_url = url.scheme + '://' + url.netloc.split(':')[0] + path + querystring
    req = AWSRequest(method=method.upper(), url=safe_url, data=body)
    SigV4Auth(session.get_credentials(), "execute-api", region).add_auth(req)
    return dict(req.headers.items())


if __name__ == "__main__":
    method = sys.argv[1]
    url = sys.argv[2]

    if not sys.stdin.isatty():
        body = sys.stdin.read()
    else:
        body = None

    r = requests.request(method, url, headers=get_signature_headers(method, url, body), data=body)
    print(r.content.decode("utf-8"))
