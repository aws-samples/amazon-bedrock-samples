import os
import requests
from boto3.session import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class SigV4HttpRequester:
    def __init__(self):
        self.credentials = Session().get_credentials().get_frozen_credentials()

    def send_signed_request(
        self,
        url,
        method='GET',
        body=None,
        params=None,
        headers=None,
        service='execute-api',
        region=None
    ):
        if region is None:
            region = os.environ['AWS_REGION'] if 'AWS_REGION' in os.environ else None

        # sign request
        req = AWSRequest(
            method=method,
            url=url,
            data=body,
            params=params,
            headers=headers
        )
        SigV4Auth(self.credentials, service, region).add_auth(req)
        req = req.prepare()

        # send request
        response = requests.request(
            method=req.method,
            url=req.url,
            headers=req.headers,
            data=req.body
        )

        return response

'''Example usage:
if __name__ == "__main__":
    requester = SigV4HttpRequester()
    response = requester.send_signed_request(
        url='https://www.example.com',
        method='GET',
        body=json.dumps({ 'foo': 'bar' }),
        headers={ 'content-type': 'application/json' }
    )
    print(response.status_code)
    print(response.text)'''