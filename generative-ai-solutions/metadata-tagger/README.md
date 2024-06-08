# Claude 3 - Metadata Extraction Capability

This repo provides code samples for Claude 3 to extract metadata from text. The schema for the metadata is provided as part of the prompt. This example uses synthetic data to demonstrate the metadata extraction capability for Claude 3. The extracted metadata is provided in JSON format so that it is parseable by downstream applications.

## Bring your own Schema/Documents

1. To use your custom schema, enter the schema in the notebook as given in the example below. The provided example defines the structure and data types for generating metadata on physics-based documents. It specifies that each document should have an article title (string), author (string), topic (string), and an optional publication date (string). This schema ensures consistent and organized metadata for the documents, enabling efficient indexing, searching, and categorization of content.

    ```{.markdown}
    YOUR_SCHEMA: Dict = {
        "properties": {
            "article_title": {"type": "string"},
            "author": {"type": "string"},
            "topic": {"type": "string", "enum": ["quantum physics",
                                                 "classical mechanics",
                                                 "thermodynamics",
                                                 "relativity",
                                                 "other"]},
            "publication_date": {
                "type": "string",
                "description": "The date the article was published, say \"date unknown\" if not found",
            },
        },
        "required": ["article_title", "author", "topic"],
    }
    ```

2. View an example of a document that is used to generate metadata on:

- **Example document**:

    ```{.markdown}
    "Title: Quantum Entanglement\nAuthor: John Doe\n\nAn in-depth look at the fascinating world of quantum entanglement. Published 2022-03-04.",
    ```

- **Metadata generated**: The metadata generated using Claude 3 is generated in JSON format. This can be used for further analysis, enhanced document storage/retrieval and other downstream applications.

    ```{.markdown}
    Metadata: {
        "article_title": "Quantum Entanglement",
        "author": "John Doe",
        "topic": "quantum physics",
        "publication_date": "2022-03-04"
    }

    ```

## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
