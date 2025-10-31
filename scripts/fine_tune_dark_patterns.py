"""Utility script to fine-tune a transformer for dark pattern classification."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train_csv", type=Path, help="Path to the training CSV file")
    parser.add_argument("val_csv", type=Path, help="Path to the validation CSV file")
    parser.add_argument("--text-column", default="text", help="Column containing the UX copy")
    parser.add_argument("--label-column", default="label", help="Column containing labels")
    parser.add_argument("--model", default="distilbert-base-uncased", help="Base model name")
    parser.add_argument("--output-dir", default="model", help="Directory to store checkpoints")
    parser.add_argument("--epochs", type=float, default=3.0, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    return parser.parse_args()


def load_dataset(csv_path: Path, text_column: str, label_column: str) -> Dataset:
    frame = pd.read_csv(csv_path)
    if text_column not in frame or label_column not in frame:
        missing = {text_column, label_column} - set(frame.columns)
        raise ValueError(f"Missing required columns: {missing}")
    return Dataset.from_pandas(frame[[text_column, label_column]])


def tokenize_dataset(dataset: Dataset, tokenizer: AutoTokenizer, text_column: str) -> Dataset:
    def tokenize(batch: dict) -> dict:
        return tokenizer(batch[text_column], truncation=True, padding="max_length")

    return dataset.map(tokenize, batched=True)


def main(args: argparse.Namespace) -> None:
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    train_ds = load_dataset(args.train_csv, args.text_column, args.label_column)
    val_ds = load_dataset(args.val_csv, args.text_column, args.label_column)

    label_list = sorted(train_ds.unique(args.label_column))
    id2label = {idx: str(label) for idx, label in enumerate(label_list)}
    label2id = {label: idx for idx, label in id2label.items()}

    train_ds = train_ds.map(lambda example: {"labels": label2id[example[args.label_column]]})
    val_ds = val_ds.map(lambda example: {"labels": label2id[example[args.label_column]]})

    tokenized_train = tokenize_dataset(train_ds, tokenizer, args.text_column)
    tokenized_val = tokenize_dataset(val_ds, tokenizer, args.text_column)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id,
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        num_train_epochs=args.epochs,
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main(parse_args())
