const fs = require('fs');
const AWS = require('aws-sdk');
const util = require('util');
const response = require('cfn-response');

const existing_claims_table_name = process.env.EXISTING_CLAIMS_TABLE_NAME;
const docClient = new AWS.DynamoDB.DocumentClient({
    region: process.env.AWS_REGION
});
const batchSize = 25;

exports.lambda_handler = function (event, context, callback) {

    console.log("Reading input from event:\n", util.inspect(event, {depth: 5}));
    const input = event.ResourceProperties;

    if (event.RequestType === 'Delete') {
        response.send(event, context, response.SUCCESS, {});
    }

    var obj = JSON.parse(fs.readFileSync('claims.json', 'utf8'));

    var batchPutPromises = [];
    var itemArray = []
    for (var i = 0; i < obj.length; i++) {
        if (i % batchSize === 0 && i !== 0) {
            var param = {RequestItems: {}};
            param['RequestItems'][existing_claims_table_name] = itemArray;
            batchPutPromises.push(docClient.batchWrite(param).promise());
            itemArray = [];
        }
        itemArray.push({PutRequest: {Item: obj[i]}});
    }
    var param = {RequestItems: {}};
    param['RequestItems'][existing_claims_table_name] = itemArray;
    batchPutPromises.push(docClient.batchWrite(param).promise());

    Promise.all(batchPutPromises).then(data => {
        console.log("done loading " + obj.length + " rows.");
        response.send(event, context, response.SUCCESS, {});
    }).catch(err => {
        console.error(err);
        response.send(event, context, response.FAILED, err);
    })
}

