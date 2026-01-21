from dataclasses import dataclass

@dataclass
class Chat_templates:
    templates={
        "qwen3-instruct":"<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant",
        "mistral":"[INST] {}[/INST]",
        "chatml":"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant",
        "gemma-3":"<start_of_turn>user\n{}<end_of_turn>\n<start_of_turn>model\n"
    }
    temp_name={
        "oss_V":"mistral",
        "oss_M":"mistral",
        "oss_L":"mistral",
        "oss_G":"gemma3",
        "oss_Q":"qwen3-instruct"
    }