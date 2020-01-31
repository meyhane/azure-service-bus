[![Build Status](https://travis-ci.org/sesam-community/azure-service-bus.svg?branch=master)](https://travis-ci.org/sesam-community/azure-service-bus)


# azure-service-bus
microservice to push to or pull from azure-service-bus

can be used to:
 * send to or receive from a queue
 * publish to a topic or receive from a subscription

### Environment Parameters

| CONFIG_NAME        | DESCRIPTION           | IS_REQUIRED  |DEFAULT_VALUE|
| -------------------|---------------------|:------------:|:-----------:|
| CONNECTION_LIST | dict. the list of connection specs the service needs to be able to access Azure Service Bus. See below for schema.| yes | n/a |
| DEFAULT_IDLE_TIMEOUT |  Default value for 'idle_timeout'. See query params for explanation | no | 30 |
| DEFAULT_PREFETCH |  Default value for 'prefetch'. See query params for explanation | no | 30 |
| PORT |  port number for the service to run on | no | 5000 |
| LOG_LEVEL | log level | no | "INFO" |

CONNECTION_LIST:
```json{
  "<my-connection-key1>": {
    "conn_str": "$SECRET(<my-connection1-string-secret>)"
  }, "<my-connection-key2>": {
      "conn_str": "$SECRET(<my-connection2-string-secret>)"
    }

}
```

### app routes

| ROUTE NO | PATH        | METHOD           |
|---|-------------------|---------------------:|
| 1| /send_message_to_topic | POST |
| 2| /send_message_to_queue | POST|
| 3| /receive_sub_messages | GET|
| 4| /receive_queue_messages | GET |


#### Query Parameters

|  NAME        | Description           | Applicable Routes |
| -------------------|:---------------------|:---------------------|
| connection_key  | The key in CONNECTION_LIST dict that the request regards | all |
| topic_name  | Name of the topic. Required if not already specified in the connection string| 1,3|
| queue_name  | Name of the queue. Required if not already specified in the connection string | 1,3|
| sub_name  |  Name of the subscription that the request regards| 3|
| session_id | Session ID of the message. Required for session enabled topics/queues. Can be sent as '*' to receive from all sessions | all|
| idle_timeout  | Number of seconds to wait in idle mode for new messages.| 3,4 |
| prefetch  | The maximum number of messages to cache with each request to the service.| 3,4 |


### Important Notes:
  * messages are received in PeekLock mode.
### An example of system config:

system:
```json
{
  "_id": "my-azure-service-bus",
  "type": "system:microservice",
  "connect_timeout": 60,
  "docker": {
    "environment": {
            "CONNECTION_LIST": {
                "my-connection": {
                    "conn_str": "$SECRET(my-connection-string-secret)"
                }
            },
            "LOG_LEVEL": "DEBUG"
        }
    },
    "image": "sesamcommunity/azure-service-bus:x.y.z",
    "port": 5000
  },
  "read_timeout": 7200,
}
```
pipe that pushes to queue
```json
{
  "_id": "my-endpoint-pipe",
  ...
  "sink": {
    "type": "json",
    "system": "my-azure-service-bus",
    "url": "/send_message_to_queue?connection_key=my-connection"
  },
  ...

}
```
pipe that pushes to session-enabled-queue
```json
{
  "_id": "my-endpoint-pipe",
  ...
  "sink": {
    "type": "json",
    "system": "my-azure-service-bus",
    "url": "/send_message_to_queue?connection_key=my-connection&sesion_id=session1"
  },
  ...

}
```

pipe that reads from queue
```json
{
  "_id": "my-endpoint-pipe",
  ...
  "source": {
    "type": "json",
    "system": "my-azure-service-bus",
    "url": "/receive_queue_messages?connection_key=my-connection"
  },
  ...

}
```

pipe that reads from session-enabled-queue
```json
{
  "_id": "my-endpoint-pipe",
  ...
  "sink": {
    "type": "json",
    "system": "my-azure-service-bus",
    "url": "/receive_queue_messages?connection_key=my-connection"
  },
  ...

}
```

pipe that reads subscription messages for subscription 'S'
```json
{
  "_id": "my-endpoint-pipe",
  ...
  "sink": {
    "type": "json",
    "system": "my-azure-service-bus",
    "url": "/receive_sub_messages?connection_key=my-connection&sub_name=S"
  },
  ...

}
```
