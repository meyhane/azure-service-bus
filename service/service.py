from flask import Flask, request, Response, abort
from werkzeug.exceptions import BadRequestKeyError
import requests
from azure.servicebus import Message, TopicClient, SubscriptionClient, QueueClient
from azure.servicebus.common.errors import NoActiveSession
from azure.servicebus.common.constants import NEXT_AVAILABLE
import json
import os
import sys
from sesamutils import sesam_logger
from sesamutils.flask import serve


app = Flask(__name__)

logger = sesam_logger("azure-service-bus", app)

try:
    PORT = int(os.environ.get('PORT', 5000))
    CONNECTION_LIST=json.loads(os.environ['CONNECTION_LIST'])
    DEFAULT_IDLE_TIMEOUT=int(os.environ.get('DEFAULT_IDLE_TIMEOUT', 30))
    DEFAULT_PREFETCH=int(os.environ.get('DEFAULT_PREFETCH', 30))
except (ValueError, KeyError) as er:
    logger.exception(er)
    sys.exit(1)

def respond(status_code, message):
    return Response(
        response=json.dumps({"success": str(status_code)[0] in ['2','3'], 'message': message}),
        status=status_code,
        mimetype='application/json')

@app.route("/send_message_to_topic", methods=["POST"], endpoint='TOPIC_MSG_RECEIVER_ENDPOINT')
@app.route("/send_message_to_queue", methods=["POST"], endpoint='QUEUE_MSG_RECEIVER_ENDPOINT')
def send_message():
    try:
        try:
            conn_key = request.args['connection_key']
            conn_str = CONNECTION_LIST[conn_key]['conn_str']
            topic_name = request.args.get('topic_name')
            queue_name = request.args.get('queue_name')
            session_id = request.args.get('session_id')
        except (BadRequestKeyError, ValueError) as er:
            return respond(400, 'invalid parameter values')

        client = None
        if request.endpoint == 'TOPIC_MSG_RECEIVER_ENDPOINT':
            client = TopicClient.from_connection_string(conn_str=conn_str, name=topic_name)
        elif request.endpoint == 'QUEUE_MSG_RECEIVER_ENDPOINT':
            client = QueueClient.from_connection_string(conn_str=conn_str, name=queue_name)
        else:
            return respond(404,'not found')

        request_data = request.get_json()
        msg_list = None
        if isinstance(request_data, dict):
            msg_list = [Message(json.dumps(request_data))]
        elif isinstance(request_data, list):
            msg_list = [Message(json.dumps(msg)) for msg in request_data]

        response_data=[]
        if msg_list:
            send_result_list = client.send(messages=msg_list, message_timeout=0, session=session_id)
            for i, send_result in enumerate(send_result_list):
                response_data.append(send_result)
                if not send_result[0]:
                    logger.warning('failed to send msg for message %s(index %d with message %s)'%(msg_list[i].body, i, send_result[1]))
        return respond(200, response_data)
    except Exception as er:
        logger.exception(er)
        return respond(500, str(er))

@app.route("/receive_sub_messages", methods=["GET"], endpoint='SUBSCRIPTION_MSG_PUBLISHER_ENDPOINT')
@app.route("/receive_queue_messages", methods=["GET"], endpoint='QUEUE_MSG_PUBLISHER_ENDPOINT')
def receive_messages():
    try:
        try:
            conn_key = request.args['connection_key']
            conn_str = CONNECTION_LIST[conn_key]['conn_str']
            sub_name = request.args['sub_name'] if request.endpoint == 'SUBSCRIPTION_MSG_PUBLISHER_ENDPOINT' else None
            topic_name = request.args.get('topic_name')
            queue_name = request.args.get('queue_name')
            session_id = request.args.get('session_id')
            idle_timeout = int(request.args.get('idle_timeout', DEFAULT_IDLE_TIMEOUT))
            prefetch = int(request.args.get('prefetch', DEFAULT_PREFETCH))
        except (BadRequestKeyError, ValueError) as er:
            logger.info('request args %s' % request.args)
            return respond(400, 'invalid parameter values')

        client = None
        if request.endpoint == 'SUBSCRIPTION_MSG_PUBLISHER_ENDPOINT':
            client = SubscriptionClient.from_connection_string(conn_str, name=sub_name, topic=topic_name)
        elif request.endpoint == 'QUEUE_MSG_PUBLISHER_ENDPOINT':
            client = QueueClient.from_connection_string(conn_str, name=queue_name)


        response_body = bytearray()
        response_body += b'['
        is_first = True
        while True:
            try:
                if session_id == '*':
                    session_id = NEXT_AVAILABLE
                with client.get_receiver(session=session_id, idle_timeout=idle_timeout, prefetch=prefetch) as msg_receiver:
                    msg_batch = msg_receiver.fetch_next(max_batch_size=prefetch, timeout=1)
                    while msg_batch:
                        for msg in msg_batch:
                            msg_body = bytearray()
                            for bytes in msg.body:
                                msg_body += bytes
                                try:
                                    if json.loads(msg_body):
                                        if is_first:
                                            is_first = False
                                        else:
                                            response_body += b','
                                        response_body += msg_body
                                        msg.complete()
                                except json.JSONDecodeError as er:
                                    logger.warning('not deleting fetched messages from service bus due to failed JSON serialization')

                        msg_batch = msg_receiver.fetch_next(max_batch_size=None, timeout=1)
                if session_id != '*':
                    break
            except NoActiveSession as err:
                break
        response_body += b']'

        return Response(response=response_body, mimetype='application/json')
    except Exception as er:
        logger.exception(er)
        return respond(500, str(er))


if __name__ == "__main__":
    serve(app, port=PORT)
