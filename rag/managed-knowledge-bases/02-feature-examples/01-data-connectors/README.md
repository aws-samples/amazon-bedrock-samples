# Data Connectors

Connect your Managed Knowledge Base to various data sources.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01-web-crawler-connector.ipynb` | Web Crawler connector — crawl and ingest web pages |
| 03 | `03-sharepoint-connector.ipynb` | SharePoint connector — ingest from SharePoint sites |
| 04 | `04-onedrive-connector.ipynb` | OneDrive connector — ingest from OneDrive |
| 05 | `05-googledrive-connector.ipynb` | Google Drive connector — ingest from Google Drive | - Coming soon

## Supported connectors

| Connector | Type | Auth required |
|-----------|------|---------------|
| S3 | `S3` | IAM (bucket policy) |
| Web Crawler | `WEB` | Optional (basic, form, SAML) |
| SharePoint | `SHAREPOINT` | OAuth2 / Entra ID (Secrets Manager) |
| OneDrive | `ONEDRIVE` | OAuth2 (Secrets Manager) |
| Google Drive | `GOOGLEDRIVE` | OAuth2 (Secrets Manager) |
| Confluence | `CONFLUENCE` | OAuth2 (Secrets Manager) |
| Custom | `CUSTOM` | Varies |

## Documentation

- [Connect a data source](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-connect-ds.html)
- [Supported data source connectors](https://docs.aws.amazon.com/bedrock/latest/userguide/data-source-connectors.html)
