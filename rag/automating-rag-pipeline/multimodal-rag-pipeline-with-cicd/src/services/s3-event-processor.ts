
const handler = async (event: any): Promise<any> => {
    console.log('Event: ', event);

    // Extract the file name and event type
    const fileName = event.detail.object.key;
    const eventType = event['detail-type'];

    // Create a new JSON output
    const typeOfS3Event = {
        fileName: fileName,
        eventType: eventType
    };

    console.log('S3 Event Processor Lambda Output: ', typeOfS3Event);

    // return {
    //     statusCode: 200,
    //     body: JSON.stringify(typeOfS3Event)
    // };

    // Return the response directly without wrapping it in a Payload object
    return typeOfS3Event;
}

export { handler }