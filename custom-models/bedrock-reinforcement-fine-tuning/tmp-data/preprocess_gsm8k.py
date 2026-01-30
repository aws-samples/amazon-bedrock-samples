# Single cell to preprocess GSM8K from HuggingFace into Bedrock RFT format
# Usage: Provide HF dataset path (e.g., "openai/gsm8k") and run

from datasets import load_dataset
import json, re

def preprocess_gsm8k(hf_path="openai/gsm8k", train_size=256, test_size=256, output_dir="."):
    ds = load_dataset(hf_path, "main")
    
    def extract_answer(answer_text):
        match = re.search(r'####\s*(-?\d+(?:,\d+)*)', answer_text)
        return match.group(1).replace(',', '') if match else ""
    
    def format_row(row, idx, split):
        return {
            "data_source": hf_path,
            "prompt": [{"content": f"{row['question']} Let's think step by step and output the final answer after \"####\".", "role": "user"}],
            "ability": "math",
            "reward_model": {"ground_truth": extract_answer(row['answer']), "style": "rule"},
            "extra_info": {"answer": row['answer'], "index": idx, "question": row['question'], "split": split}
        }
    
    for split, size, filename in [("train", train_size, "train.jsonl"), ("test", test_size, "test.jsonl")]:
        with open(f"{output_dir}/{filename}", "w") as f:
            for i, row in enumerate(ds[split].select(range(min(size, len(ds[split]))))):
                f.write(json.dumps(format_row(row, i, split)) + "\n")
        print(f"Wrote {filename}")

if __name__ == "__main__":
    preprocess_gsm8k(output_dir=".")
