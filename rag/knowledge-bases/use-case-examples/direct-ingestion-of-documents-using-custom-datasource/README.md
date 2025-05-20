Amazon Bedrock Knowledge Bases now supports custom connector and ingestion of streaming data, allowing developers to add, update, or delete data in their knowledge base through direct API calls.  With this new capability, customers can easily ingest specific documents from custom data sources or Amazon S3 without requiring a full sync, and ingest streaming data without the need for intermediary storage.  You can use custom connectors in cases where a native connector is not yet supported.

There are two notebooks showing direct ingestion of documents using a custom datasource.  The first uses JIRA as a datasource and the second uses Google Drive.  Instructions and screenshots can be found here:

[Jira Instructions](./JIRA-API-Access.pdf)

[Google Drive Instructions](./Google-Drive-API-Access.pdf)

Note:  This example doesn’t include ingestion management at scale (for example queuing and retry logic).