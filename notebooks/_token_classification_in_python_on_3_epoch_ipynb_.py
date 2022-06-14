# -*- coding: utf-8 -*-
""""Token Classification in Python on 3 epoch.ipynb"

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1qVYog5HJJE8cpp_rm0Mnkb5eJseT5IfC
"""
!pip install datasets==2.1.0 seaborn==0.11.2 scikit-learn==1.0.2 gensim==4.2.0 nltk==3.7 pymystem3==0.2.0 transformers==4.19.4 seqeval==1.2.2

import pickle
import numpy as np
from transformers import Trainer
from datasets import load_metric
from datasets import load_dataset
from transformers import AutoTokenizer
from transformers import TrainingArguments
from transformers import AutoModelForTokenClassification
from transformers import DataCollatorForTokenClassification

raw_dataset = load_dataset('surdan/nerel_short')
tokenizer = AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased-sentence")


def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(examples["sequences"], truncation=True, is_split_into_words=True)

    labels = []
    for i, label in enumerate(examples[f"ids"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)  # Map tokens to their respective word.
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:  # Set the special tokens to -100.
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:  # Only label the first token of a given word.
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)
            previous_word_idx = word_idx
        labels.append(label_ids)

    tokenized_inputs["labels"] = labels
    return tokenized_inputs


tokenized_dataset = raw_dataset.map(
    tokenize_and_align_labels,
    batched=True,
    remove_columns=raw_dataset["train"].column_names
)

data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

with open('../id_to_label_map.pickle', 'rb') as f:
    map_id_to_label = pickle.load(f)

id2label = {str(k): v for k, v in map_id_to_label.items()}
label2id = {v: k for k, v in id2label.items()}
label_names = list(id2label.values())

model = AutoModelForTokenClassification.from_pretrained("DeepPavlov/rubert-base-cased-sentence", id2label=id2label,
                                                        label2id=label2id)

## for compute_metrics function


metric = load_metric("seqeval")


def compute_metrics(eval_preds):
    """
    Function for evaluate model
    
    :param eval_preds: model output
    :type eval_preds: 
    """
    logits, labels = eval_preds
    predictions = np.argmax(logits, axis=-1)

    # Remove ignored index (special tokens) and convert to labels
    true_labels = [[label_names[l] for l in label if l != -100] for label in labels]
    true_predictions = [[label_names[p] for (p, l) in zip(prediction, label) if l != -100]
                        for prediction, label in zip(predictions, labels)
                        ]
    all_metrics = metric.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": all_metrics["overall_precision"],
        "recall": all_metrics["overall_recall"],
        "f1": all_metrics["overall_f1"],
        "accuracy": all_metrics["overall_accuracy"],
    }


training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    save_strategy="no",
    learning_rate=2e-5,
    num_train_epochs=3,
    weight_decay=0.01,
    push_to_hub=False,
    per_device_train_batch_size=4  ## depending on the total volume of memory of your GPU
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["dev"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    data_collator=data_collator,
)

trainer.train()
trainer.save_model('./saved_model')  # For reuse

trainer.evaluate()

from transformers import pipeline

# Replace this with your own checkpoint
model_checkpoint = "/content/saved_model"
token_classifier = pipeline(
    "token-classification", model=model_checkpoint, aggregation_strategy="simple"
)

token_classifier(
    "Отвечая на вопрос, кто принял решение о закрытии воздушного пространства Черногории для борта Лаврова, Кривокапич отметил, что формально решение принято правительством и министерством иностранных дел страны.")
