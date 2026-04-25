import json

with open('grpo_disaster_training.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        new_source = []
        for line in cell['source']:
            line = line.replace('unsloth/Qwen2.5-1.5B-Instruct', 'unsloth/Qwen2.5-7B-Instruct-bnb-4bit')
            line = line.replace('model.push_to_hub("joynnayvedya/disaster-response-trained")', 'model.push_to_hub_merged("joynnayvedya/disaster-response-trained", tokenizer, save_method="merged_16bit", token=os.environ.get("HF_TOKEN"))')
            if 'tokenizer.push_to_hub' in line:
                line = ''
            new_source.append(line)
        cell['source'] = new_source

with open('grpo_disaster_training.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
