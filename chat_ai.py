from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_name = "cyberagent/open-calm-3b"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def generate(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_length=200,
        temperature=0.8,
        do_sample=True,
        top_p=0.95
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print(generate("日本の夏について説明して"))
