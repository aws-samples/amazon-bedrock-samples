
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

def model_fn(model_dir):
  # Load model from HuggingFace Hub
  tokenizer = AutoTokenizer.from_pretrained(model_dir)
  model = AutoModelForSequenceClassification.from_pretrained(model_dir)
  model.eval()
  return model, tokenizer

def predict_fn(data, model_and_tokenizer):
    model, tokenizer = model_and_tokenizer
    query = data['query']
    documents = data['documents']
    topk = data['topk']
    pair_list = [ [ query, x ] for x in documents ]
    with torch.no_grad():
        inputs = tokenizer(pair_list, padding=True, truncation=True, return_tensors='pt', max_length=512)
        scores = model(**inputs, return_dict=True).logits.view(-1, ).float()
        print(scores)
        sorted_indexes = sorted(range(len(scores)), key=lambda k: scores[k], reverse=True)[:topk]
        response = [ { "index" : x, "score" : scores[x] } for x in sorted_indexes ]
        return response
