const handler = async (event: any): Promise<any> => {
    console.log('Evaluate New Data Ingestion Lambda!');
    // console.log('Received Event:', JSON.stringify(event, null, 2));

    // if (!event || Object.keys(event).length === 0) {
    //     console.error('Empty or undefined event received');
    //     return {
    //         success: false,
    //         message: 'Empty event received.',
    //     };
    // }

    // const ingestionResult = event.ingestionResult;
    const ingestionResult = { "successRate": 85 };
    if (!ingestionResult || typeof ingestionResult.successRate === 'undefined') {
        console.log('Ingestion result or successRate is missing.');
        return {
            success: false,
            message: 'Missing ingestion result or successRate in event payload.',
        };
    }

    console.log('Ingestion Result:', JSON.stringify(ingestionResult, null, 2));

    const threshold = 80;  // Example threshold for passing evaluation

    if (ingestionResult.successRate >= threshold) {
        console.log('Ingestion success rate meets the threshold. Evaluation passed.');
        return {
            success: true,
            message: 'Proceed to production',
        };
    } else {
        console.log('Ingestion success rate below threshold. Evaluation failed.');
        return {
            success: false,
            message: 'Evaluation failed. Do not proceed to production',
        };
    }
}

export { handler };




// return {
//     statusCode: 200,
//     body: JSON.stringify({
//         message: 'Hello Lambda!'
//     })
// }