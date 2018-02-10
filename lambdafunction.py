import boto3
import json

client = boto3.client("dynamodb")
client2 = boto3.client('iot-data')

#client3 = boto3.client('sns')

def lambda_handler(event, context):
    
    timestamp = event['timestamp']
    temperature = event['temperature']
    humidity = event['humidity']
    
    response = client2.publish(
     topic='sensors/temperature',
     qos=1,
     payload=json.dumps({'temperature':temperature})
    ) 
    
    response = client2.publish(
     topic='sensors/humidity',
     qos=1,
     payload=json.dumps({'humidity':humidity})
    ) 
    
    response = client.put_item(
     TableName='temp_humid',
     Item={
      'timestamp':{'S':timestamp},'temperature':{'S':temperature},'humidity':{'S':humidity}
            
        }
    )
    
    
   # if temp >24:
    #    response = client3.publish(
     #       topic='snstopic'
      #      payload=json.dumps({'default': json.dumps(message)}),
       # )
    
    # TODO implement
    return 'Hello from Lambda'