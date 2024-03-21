# Amazon Berkeley Objects (c) by Amazon.com

[Amazon Berkeley Objects](https://amazon-berkeley-objects.s3.us-east-1.amazonaws.com/index.html)
is a collection of product listings with multilingual metadata, catalog
imagery, high-quality 3d models with materials and parts, and benchmarks derived
from that data.

## License

This work is licensed under the Creative Commons Attribution 4.0 International
Public License. To obtain a copy of the full license, see LICENSE-CC-BY-4.0.txt,
visit [CreativeCommons.org](https://creativecommons.org/licenses/by/4.0/)
or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

Under the following terms:

  * Attribution — You must give appropriate credit, provide a link to the
    license, and indicate if changes were made. You may do so in any reasonable
    manner, but not in any way that suggests the licensor endorses you or your
    use.

  * No additional restrictions — You may not apply legal terms or technological
    measures that legally restrict others from doing anything the license
    permits.
    
## Attribution

Credit for the data, including all images and 3d models, must be given to:

> Amazon.com

Credit for building the dataset, archives and benchmark sets must be given to:

> Matthieu Guillaumin (Amazon.com), Thomas Dideriksen (Amazon.com),
> Kenan Deng (Amazon.com), Himanshu Arora (Amazon.com),
> Jasmine Collins (UC Berkeley) and Jitendra Malik (UC Berkeley)

## Description

The `listings/` directory and `abo-listings.tar` archive are made of the
following files:

  * `LICENSE-CC-BY-4.0.txt` - The License file. You must read, agree and
    comply to the License before using the Amazon Berkeley Objects data.

  * `listings/metadata/listings_<i>.json.gz` - Product description and metadata.
    Each of the 16 files is encoded with UTF-8 and gzip-compressed. Each line of
    the decompressed files corresponds to one product as a JSON object (see
    http://ndjson.org/ or https://jsonlines.org/ ). Each product JSON object
    (a.k.a dictionary) has any number of the following keys:
    
    - `brand`
        - Content: Brand name
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `bullet_point`
        - Content: Important features of the products
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `color`
        - Content: Color of the product as text
        - Format: `[{"language_tag": <str>, "standardized_values": [<str>],
          "value": <str>}, ...]`
    - `color_code`
        - Content: Color of the product as HTML color code
        - Format: `[<str>, ...]`
    - `country`
        - Content: Country of the marketplace, as an
          [ISO 3166-1 alpha 2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)
          code
        - Format: `<str>`
    - `domain_name`
        - Content: Domain name of the marketplace where the product is found.
          A product listing in this collection is uniquely identified by
          (`item_id`, `domain_name`)
        - Format: `<str>`
    - `fabric_type`
        - Content: Description of product fabric
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `finish_type`
        - Content: Description of product finish
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `item_dimensions`
        - Content: Dimensions of the product (height, width, length)
        - Format: `{"height": {"normalized_value": {"unit": <str>, "value":
          <float>}, "unit": <str>, "value": <float>}, "length":
          {"normalized_value": {"unit": <str>, "value": <float>}, "unit": <str>,
          "value": <float>}, "width": {"normalized_value": {"unit": <str>,
          "value": <float>}, "unit": <str>, "value": <float>}}}`
    - `item_id`
        - Content: The product reference id. A product listing in this
          collection is uniquely identified by (`item_id`, `domain_name`).
          A corresponding product page may exist at
          `https://www.<domain_name>/dp/<item_id>` [^1]
        - Format: `<str>`
    - `item_keywords`
        - Content: Keywords for the product
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `item_name`
        - Content: The product name
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `item_shape`
        - Content: Description of the product shape
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `item_weight`
        - Content: The product weight
        - Format: `[{"normalized_value": {"unit": <str>, "value": <float>},
          "unit": <str>, "value": <float>}, ...]`
    - `main_image_id`
        - Content: The main product image, provided as an `image_id`. See the
          descripton of `images/metadata/images.csv.gz` below
        - Format: `<str>`
    - `marketplace`
        - Content: Retail website name (Amazon, AmazonFresh, AmazonGo, ...)
        - Format: `<str>`
    - `material`
        - Content: Description of the product material
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `model_name`
        - Content: Model name
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `model_number`
        - Content: Model number
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `model_year`
        - Content: Model year
        - Format: `[{ "language_tag": <str>, "value": <int> }, ...]`
    - `node`
        - Content: Location of the product in the category tree. A node page
          may exist at `https://www.<domain_name>/b/?node=<node_id>` [^1] for
          browsing
        - Format: `[{ "node_id": <int>, "path": <str>}, ...]`
    - `other_image_id`
        - Content: Other available images for the product, provided as
          `image_id`. See the description of `images/metadata/images.csv.gz`
          below
        - Format: `[<str>, ...]`
    - `pattern`
        - Content: Product pattern
        - Format: `[{ "language_tag": <str>, "value": <int> }, ...]`
    - `product_description`
        - Content: Product description as HTML 
        - Format: `[{ "language_tag": <str>, "value": <int> }, ...]`
    - `product_type`
        - Content: Product type (category)
        - Format: `<str>`
    - `spin_id`
        - Content: Reference to the 360º View image sequence. See the
          description of `spins/metadata/spins.csv.gz` below
        - Format: `<str>`
    - `style`
        - Content: Style of the product
        - Format: `[{ "language_tag": <str>, "value": <str> }, ...]`
    - `3dmodel_id`
        - Content: Reference to the 3d model of the product. See the description
          of `3dmodels/metadata/3models.csv.gz`
        - Format: `<str>`

## Footnotes

[^1]: Importantly, there is no guarantee that these URLs will remain unchanged
and available on the long term, we thus recommend using the images provided in
the archives instead.
