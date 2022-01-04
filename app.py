import json
import os
import string

import boto3
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request
# PyPI package name is aws-wsgi
import awsgi

lambda_client = boto3.client('lambda')
# TODO - put these in a config.py and programattically get the arns from params store or by discovery
wfr_benefits_integration_arn = os.environ.get('wfr_benefits_integration_arn')
nsm_integration_hr_empreports_arn = os.environ.get('nsm_integration_hr_empreports_arn')
empsync_arn = os.environ.get('empsync_arn')
app = Flask(__name__)


def dict_to_string(dict_object) -> string:
    """
    Takes in a dictionary object and returns a string
    :param dict_object: Dictionary object
    :return: string representation of the dictionary
    """
    key_values = vars(dict_object).items()
    new_dict = {str(key): str(value) for key, value in key_values}
    return json.dumps(new_dict)


def get_request_meta():
    """
    Gets the request metadata such as event as context (Lambda metas).
    :return: event, context, and event_body
    """
    event = request.environ.get('awsgi.event', {})
    context = dict_to_string(request.environ.get('awsgi.context', {}))
    event_body = event['body']
    return event, context, event_body


def invoke_lambda_async(name, payload, client_context, invocation_type='Event', log_type='None'):
    """
    Invokes an AWS Lambda function
    :param name: The name of the Lambda function, version, or alias. Function name, ARN, partial ARN are acceptable.
    :param payload: The JSON that you want to provide to your Lambda function as input.
    :param invocation_type: Choose from the following options:
        RequestResponse (default) - Invoke the function synchronously. Keep the connection open until the function returns a response or times out. The API response includes the function response and additional data.
        Event - Invoke the function asynchronously. Send events that fail multiple times to the function's dead-letter queue (if it's configured). The API response only includes a status code.
        DryRun - Validate parameter values and verify that the user or role has permission to invoke the function.
    :param log_type: Set to Tail to include the execution log in the response. Applies to synchronously invoked functions only. 'None'|'Tail' are acceptable
    :param client_context: Up to 3583 bytes of base64-encoded data about the invoking client to pass to the function in the context object.
    # :param qualifier: Specify a version or alias to invoke a published version of the function.
    :return:
    """
    try:
        response = lambda_client.invoke(
            FunctionName=name,
            InvocationType=invocation_type,
            LogType=log_type,
            ClientContext=client_context,
            Payload=payload.encode(),
            # Qualifier (string) -- Specify a version or alias to invoke a published version of the function.
            # Qualifier=qualifier
        )
        status_code = response['StatusCode']
        response = f'OK - lambda {name} invoked successfully'
    except ClientError as e:
        response = e.args[0]
        status_code = 500

    return status_code, response


@app.route('/', methods=['GET'])
def root():
    return jsonify(status=200, message='i am root')


@app.route('/hello', methods=['GET'])
def hello():
    return jsonify(status=200, message='hello')


@app.route('/wfr', methods=['POST'])
def wfr():
    _, context, event_body = get_request_meta()
    status, response = invoke_lambda_async(wfr_benefits_integration_arn, event_body, context)
    return jsonify(status=status, message=response)


@app.route('/empreports', methods=['POST'])
def empreports():
    _, context, event_body = get_request_meta()
    status, response = invoke_lambda_async(nsm_integration_hr_empreports_arn, event_body, context)
    return jsonify(status=status, message=response)


def lambda_handler(event, context):
    return awsgi.response(app, event, context, base64_content_types={'application/json'})
