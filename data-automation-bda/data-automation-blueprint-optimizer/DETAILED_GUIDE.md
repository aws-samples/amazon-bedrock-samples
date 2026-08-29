# Detailed Guide to Sequential BDA Optimization

This guide explains in simple terms how the BDA optimization application works, what each component does, and what happens when you run it.

## What is this application?

This application helps improve document extraction from PDFs using Amazon Bedrock Data Analysis (BDA). It tries different ways to ask for information from documents until it gets good results.

Think of it like teaching someone to find information in a book. If your first instruction doesn't work well ("look for the author's name"), you might try a different approach ("check the cover page for who wrote it").

The application now supports two approaches:

1. **Template-based approach**: Uses predefined templates to generate instructions
2. **LLM-based approach (default)**: Uses AI to generate and improve instructions based on previous attempts

## Key Components Explained

### 1. Input File (input_0.json)

**What it is:** This is the starting point of the application. It contains:
- Connection details for AWS services
- The document to analyze (a PDF file in S3)
- Fields you want to extract from the document
- Instructions for each field
- Expected output for each field

**Example:**
```json
{
  "project_arn": "arn:aws:bedrock:us-west-2:123456789012:data-automation-project/abcdef",
  "blueprint_id": "12345",
  "input_document": "s3://my-bucket/input/Contract.pdf",
  "inputs": [
    {
      "instruction": "Extract the contract type from the document",
      "field_name": "Contract type",
      "expected_output": "Service Agreement"
    },
    {
      "instruction": "Extract the vendor name from the contract",
      "field_name": "Vendor name",
      "expected_output": "Acme Corp"
    }
  ]
}
```

**In simple terms:** It's like a form you fill out to tell the application what document to analyze and what information to look for.

### 2. Schema File (schema.json)

**What it is:** This file defines the structure of the extraction blueprint in AWS BDA. It contains:
- The JSON schema version
- A description of the document
- The document class
- Properties (fields) to extract
- Instructions for each field

**Example:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "description": "This is a service agreement between Company A and Company B",
  "class": "Contract",
  "type": "object",
  "properties": {
    "Contract type": {
      "type": "string",
      "inferenceType": "explicit",
      "instruction": "Extract the contract type from the document"
    },
    "Vendor name": {
      "type": "string",
      "inferenceType": "explicit",
      "instruction": "Extract the vendor name from the contract"
    }
  }
}
```

**In simple terms:** It's like a blueprint that tells AWS BDA what to look for in the document and how to find it.

### 3. Instruction Generation Approaches

#### Template-based Approach

**What it is:** This is the original approach that uses predefined templates to generate instructions.

**Templates available:**
- **Original**: The instruction you provided initially
- **Direct**: A simplified, direct instruction (e.g., "Extract the [field] from the document")
- **Context**: Adds context about where to find the information
- **Format**: Specifies the expected format of the output
- **Document**: Uses the document itself to guide extraction

**Example of templates for "Contract type":**
- Original: "Determine and extract if the contract pertains to goods or services"
- Direct: "Extract the Contract type from the document"
- Context: "Look at the header section of the document and extract the Contract type"
- Format: "Extract the Contract type from the document. The output should be a short phrase like 'Service Agreement' or 'Purchase Order'"

#### LLM-based Approach (Default)

**What it is:** This new approach uses AI (Large Language Models) to generate and improve instructions based on previous attempts.

**How it works:**
1. **Initial instruction**: The AI generates an instruction based on the field name and expected output
2. **Improved instruction**: For subsequent attempts, the AI generates better instructions by learning from previous attempts and their results
3. **Document-based instruction**: For the final attempt (if enabled), the AI uses the document content to generate highly specific instructions

**Example of LLM-generated instructions for "Contract type":**
- Initial: "Extract the contract type from the document"
- Improved: "Find and extract the contract type, which should be similar to 'Service Agreement'"
- Document-based: "Look for the contract type in the header section on page 1, usually labeled as 'Agreement Type' or 'Contract Category'"

**Why it's better:** The AI can learn from previous attempts and adapt its instructions based on what works and what doesn't. It can also understand the document content and generate more specific instructions.

**In simple terms:** Instead of using fixed templates, the application now uses AI to create custom instructions that get better with each attempt, like having an expert who learns from experience.

### 4. Field Type Detection

**What it is:** The application now automatically detects what type of information each field contains.

**Types it can detect:**
- **Text**: General text like names, descriptions, etc.
- **Date**: Dates in various formats
- **Numeric**: Numbers, amounts, prices, etc.
- **Email**: Email addresses
- **Phone**: Phone numbers
- **Address**: Physical addresses

**Why it matters:** Different types of information need different extraction approaches. For example, extracting a date requires different instructions than extracting a name.

**In simple terms:** It's like knowing whether you're looking for a number, a date, or a name before you start searching.

### 5. Field History Tracking

**What it is:** The application now keeps track of all previous attempts for each field.

**What it tracks:**
- Instructions used
- Results obtained
- Similarity scores

**Why it matters:** This history helps the AI generate better instructions by learning from what worked and what didn't.

**In simple terms:** It's like keeping notes on your previous attempts so you can learn from them and do better next time.

## What Happens When You Run the Application

### Step 1: Initialization

1. The application reads the input file (`input_0.json`)
2. It connects to AWS services
3. It loads the schema file from AWS BDA
4. It sets up strategies for each field (starting with "original" instructions)
5. It initializes field histories for tracking previous attempts
6. It detects the type of each field based on its name and expected output

### Step 2: First Iteration

1. The application generates instructions:
   - If using template-based approach: It uses the current strategy template
   - If using LLM-based approach (default): It uses AI to generate initial instructions
2. It creates a new schema file with the current instructions
3. It updates the AWS BDA blueprint with this schema
4. It creates a new input file with the current instructions
5. It runs a BDA job to extract information from the document
6. It calculates how similar the extracted values are to the expected outputs
7. It updates field histories with the instructions, results, and similarity scores
8. For fields that don't meet the similarity threshold:
   - If using template-based approach: It updates the strategy to try a different template
   - If using LLM-based approach: It prepares to generate improved instructions in the next iteration
9. It creates a strategy report

### Step 3: Subsequent Iterations

1. The process repeats with updated instructions
2. For the LLM-based approach, the AI generates improved instructions based on previous attempts
3. New files are created for each iteration
4. If all fields meet the threshold, or if we reach the maximum iterations, the process stops
5. In the final iteration (if enabled), the document-based strategy is used for fields that have never met the threshold

### Step 4: Completion

1. The application creates a final strategy report
2. It prints a summary of the results

### Special Feature: Non-deterministic BDA Output Handling

The application now handles the fact that BDA might give different results for the same instruction in different runs:

1. It tracks fields that have ever met the threshold
2. Once a field meets the threshold, its strategy is not changed even if its similarity drops below the threshold in later iterations
3. This prevents "strategy churn" where the application keeps changing strategies unnecessarily

**In simple terms:** If a field gets a good result once, the application remembers that and doesn't try to fix what isn't broken.

## Command Line Options Explained

### --threshold (e.g., --threshold 0.6)

**What it does:** Sets how similar the extracted value must be to the expected output to be considered "good enough".

**Values:** Between 0 and 1
- Higher values (e.g., 0.9) require very close matches
- Lower values (e.g., 0.6) allow more differences

**In simple terms:** It's like setting the passing grade for the extraction. A threshold of 0.8 means the extraction must be 80% similar to the expected output.

### --use-doc

**What it does:** Enables the document-based strategy as a fallback option in the final iteration.

**How it works:** For fields that never meet the threshold, in the final iteration, the application will:

1. Read the actual document from S3
2. Extract the text content using Amazon Bedrock's Claude 3.5 Sonnet model
3. Pass the document content, field name, previous instructions, previous results, and expected output to the model
4. Ask the model to create a better instruction based on the document content
5. Use the AI-generated instruction for extraction

**In simple terms:** It's like having an AI assistant read the entire document first and then tell you exactly where and how to find the information, rather than using generic instructions.

**Note:** This option requires access to Amazon Bedrock and may incur additional costs for the AI model usage.

### --use-template

**What it does:** Uses the original template-based approach instead of the new LLM-based approach.

**In simple terms:** It's like choosing to use predefined templates instead of AI-generated instructions.

### --model (e.g., --model "anthropic.claude-3-haiku-20240307-v1:0")

**What it does:** Specifies which AI model to use for generating instructions.

**Default:** "anthropic.claude-3-5-sonnet-20241022-v2:0"

**In simple terms:** It's like choosing which AI assistant to use for generating instructions.

### --max-iterations (e.g., --max-iterations 3)

**What it does:** Sets the maximum number of times the application will try different strategies.

**Default:** 5 iterations

**In simple terms:** It's like saying "try up to this many different ways to ask for the information".

### --clean

**What it does:** Removes files from previous runs before starting.

**In simple terms:** It's like cleaning your desk before starting a new project.

## Files Generated During Execution

For each run with timestamp `TIMESTAMP`:

| File | Location | Purpose | Content |
|------|----------|---------|---------|
| `schema_N.json` | `schemas/run_TIMESTAMP/` | Blueprint schema | Updated instructions for iteration N |
| `input_N.json` | `inputs/run_TIMESTAMP/` | Input configuration | Updated instructions for iteration N |
| `df_bda_N_TIMESTAMP.csv` | `bda_output/sequential/` | Raw BDA output | Extracted values with confidence scores |
| `inference_result_TIMESTAMP.html` | `html_output/` | Visualization | HTML table of extracted values |
| `merged_df_N_TIMESTAMP.csv` | `merged_df_output/sequential/` | Merged data | BDA output with input data |
| `similarity_df_N_TIMESTAMP.csv` | `similarity_output/sequential/` | Similarity scores | How similar extracted values are to expected values |
| `report_N.csv` | `reports/run_TIMESTAMP/` | Strategy report | Current strategies and similarity scores |
| `final_report.csv` | `reports/run_TIMESTAMP/` | Final report | Final strategies and similarity scores |

## Example Walkthrough

### Template-based Approach Example

Let's say we want to extract "Contract type" and "Vendor name" from a contract:

1. We start with original instructions:
   - "Determine and extract if the contract pertains to goods or services"
   - "Extract the vendor name from the contract"

2. We run the application with a threshold of 0.8 using the template-based approach:
   ```bash
   ./run_sequential_pydantic.sh --threshold 0.8 --max-iterations 3 --use-template
   ```

3. First iteration:
   - "Vendor name" is extracted correctly (similarity 1.0)
   - "Contract type" is not extracted well (similarity 0.14)
   - The application updates the strategy for "Contract type" to "direct"

4. Second iteration:
   - "Vendor name" still uses the original instruction
   - "Contract type" now uses "Extract the Contract type from the document"
   - "Contract type" is now extracted better (similarity 0.73)

5. If the threshold is 0.8:
   - "Contract type" still doesn't meet the threshold
   - The application would try another strategy in the next iteration

6. If the threshold is 0.6:
   - Both fields meet the threshold
   - The application stops and reports success

### LLM-based Approach Example (Default)

Let's say we want to extract the same fields:

1. We start with the same input file.

2. We run the application with the default LLM-based approach:
   ```bash
   ./run_sequential_pydantic.sh --threshold 0.8 --max-iterations 3
   ```

3. First iteration:
   - The AI generates initial instructions for both fields:
     - "Extract the contract type from the document"
     - "Extract the vendor name from the document"
   - "Vendor name" is extracted correctly (similarity 1.0)
   - "Contract type" is extracted with similarity 0.75
   - Both fields are tracked in the field history

4. Second iteration:
   - "Vendor name" already met the threshold, so its instruction is kept
   - For "Contract type", the AI generates an improved instruction based on the previous attempt:
     - "Find and extract the contract type, which should be similar to 'Service Agreement'"
   - "Contract type" is now extracted better (similarity 0.85)

5. Both fields now meet the threshold, so the application stops and reports success.

### Document-based Strategy Example

Let's say we have a difficult field that doesn't meet the threshold after multiple attempts:

1. We run the application with the document-based strategy enabled:
   ```bash
   ./run_sequential_pydantic.sh --threshold 0.9 --max-iterations 3 --use-doc
   ```

2. After two iterations, "Initiative name" still hasn't met the threshold (similarity 0.77).

3. In the final iteration (iteration 3):
   - The application extracts the document content (~17,760 characters)
   - The AI generates a document-based instruction using the actual document content:
     - "Look for the initiative name in the executive summary section, typically found after 'Project:' or 'Initiative:'"
   - This might improve the extraction (e.g., to similarity 1.0) or it might not, depending on the document

4. The application reports the final results, showing which fields met the threshold and which didn't.

## Conclusion

This application uses an iterative approach to improve document extraction. It tries different ways of phrasing instructions until it gets good results or reaches the maximum number of iterations.

The key insights are:

1. **How you ask for information matters**: The phrasing of instructions significantly affects extraction quality
2. **Learning from previous attempts helps**: The LLM-based approach learns from what worked and what didn't
3. **Field type awareness improves results**: Different types of fields need different extraction approaches
4. **Document content provides context**: Using the document itself can generate more specific instructions
5. **Consistency is important**: Once a field meets the threshold, its strategy is preserved

By combining these insights, the application can find the best way to extract each field from the document, leading to more accurate and reliable document extraction.
