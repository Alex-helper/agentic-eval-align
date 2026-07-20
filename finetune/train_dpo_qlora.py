from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_pairs(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"DPO data not found: {path}. Run python eval.py --mode sample to generate failed-trace pairs.")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="QLoRA DPO training entrypoint for Qwen2.5-7B-Instruct.")
    parser.add_argument("--data", default="data/dpo_data/dpo_pairs.jsonl")
    parser.add_argument("--output", default="finetune/outputs/qwen2_5_7b_dpo_lora")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pairs = load_pairs(Path(args.data))
    print(f"Loaded {len(pairs)} DPO pairs from {args.data}")
    print("Base checkpoint: Qwen/Qwen2.5-7B-Instruct")
    print("Strategy: 4-bit QLoRA + DPO")

    if args.dry_run:
        print("Dry run passed. Install transformers/trl/peft/bitsandbytes to launch real GPU training.")
        return

    try:
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
        from trl import DPOTrainer
    except Exception as exc:  # pragma: no cover - optional heavy deps
        raise SystemExit(f"Missing training dependencies: {exc}") from exc

    model_name = "Qwen/Qwen2.5-7B-Instruct"
    dataset = Dataset.from_list(pairs)
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype="bfloat16")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=quant_config, device_map="auto", trust_remote_code=True)
    peft_config = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM")
    training_args = TrainingArguments(output_dir=args.output, per_device_train_batch_size=2, gradient_accumulation_steps=8, learning_rate=5e-5, num_train_epochs=1, logging_steps=5)
    trainer = DPOTrainer(model=model, args=training_args, train_dataset=dataset, tokenizer=tokenizer, peft_config=peft_config)
    trainer.train()
    trainer.save_model(args.output)


if __name__ == "__main__":
    main()
