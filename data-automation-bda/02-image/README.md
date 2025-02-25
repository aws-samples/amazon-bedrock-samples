# Image extraction and analysis using BDA

The Amazon Bedrock Data Automation (BDA) feature offers a comprehensive set of standard outputs for image processing to generate insights from your images. You can use these insights to enable a wide range of applications and use cases, such as content discovery, contextual ad placement, and brand safety. Here's an overview of each operation type available as part of standard outputs for images:

## Image Summary

Image summary generates a descriptive caption for an image. This feature is enabled within the standard output configuration by default.

## IAB Taxonomy

The Interactive Advertising Bureau (IAB) classification applies a standard advertising taxonomy to classify image content. For Preview, BDA will support 24 top-level (L1) categories and 85 second-level (L2) categories. To download the list of IAB categories supported by BDA, click here.

## Image Text Detection

This feature detects and extracts text that appears visually in an image and provides bounding box information, indicating the coordinates of each detected text element within the image, and confidence scores. This feature is enabled within the standard output configuration by default.

## Content Moderation

Content moderation detects inappropriate, unwanted, or offensive content in an image. For Preview, BDA will support 7 moderation categories: Explicit, Non-Explicit Nudity of Intimate parts and Kissing, Swimwear or Underwear, Violence, Drugs & Tobacco, Alcohol, Hate symbols. Explicit text in images is not flagged.

Bounding boxes and the associated confidence scores can be enabled or disabled for relevant features like text detection to provide location coordinates in the image. By default, image summary and image text detection are enabled. 

## Custom Output
You can further fine tune your extractions using custom output configuration. Custom outputs are configured with artifacts called [blueprints](https://docs.aws.amazon.com/bedrock/latest/userguide/bda-blueprint-info.html). Blueprints are a list of instructions for how to extract information from your file, allowing for transformation and adjustment of output. For more information and a detailed walkthrough of a blueprint, see Blueprints.