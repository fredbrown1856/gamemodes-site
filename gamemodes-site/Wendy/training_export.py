"""
Training data export pipeline for the Wendy public demo.
Exports conversations as encrypted Alpaca-format training data.
"""

import base64
import json
import os
from datetime import datetime
from typing import Optional

import database


def generate_encryption_key() -> str:
    """
    Generate a new AES-256 encryption key for training data exports.
    
    This is a one-time setup helper. Store the output in the
    TRAINING_ENCRYPTION_KEY environment variable.
    
    Returns:
        Base64-encoded 32-byte (256-bit) encryption key string
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode("utf-8")


def encrypt_data(data_bytes: bytes, key_b64: str) -> bytes:
    """
    Encrypt data using AES-256-GCM.
    
    Generates a random 12-byte nonce and prepends it to the ciphertext.
    
    Args:
        data_bytes: Plaintext data to encrypt
        key_b64: Base64-encoded AES-256 key
        
    Returns:
        Nonce (12 bytes) + ciphertext bytes
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    key = base64.b64decode(key_b64)
    aesgcm = AESGCM(key)
    
    # Generate random 12-byte nonce
    nonce = os.urandom(12)
    
    # Encrypt and prepend nonce
    ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
    
    return nonce + ciphertext


def decrypt_data(encrypted_bytes: bytes, key_b64: str) -> bytes:
    """
    Decrypt data that was encrypted with encrypt_data.
    
    Expects the first 12 bytes to be the nonce, followed by the ciphertext.
    
    Args:
        encrypted_bytes: Nonce + ciphertext bytes
        key_b64: Base64-encoded AES-256 key
        
    Returns:
        Decrypted plaintext bytes
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    key = base64.b64decode(key_b64)
    aesgcm = AESGCM(key)
    
    # Extract nonce (first 12 bytes) and ciphertext
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]
    
    return aesgcm.decrypt(nonce, ciphertext, None)


def format_alpaca_example(
    user_msg: str,
    assistant_msg: str,
    affinity_stage: str,
    affinity_value: int,
    position: int
) -> dict:
    """
    Format a message pair as an Alpaca-format training example.
    
    Args:
        user_msg: The user's message text
        assistant_msg: Wendy's response text
        affinity_stage: Current affinity stage label (e.g. "Stranger", "Friendly")
        affinity_value: Current affinity numeric value
        position: Message position in the conversation (0-indexed)
        
    Returns:
        Dict in Alpaca format with instruction, input, output, and context
    """
    return {
        "instruction": (
            "You are Wendy, a 22-year-old woman from the Appalachian mountains "
            "of eastern Kentucky. Respond in character using Appalachian dialect."
        ),
        "input": user_msg,
        "output": assistant_msg,
        "context": {
            "affinity_stage": affinity_stage,
            "affinity_value": affinity_value,
            "conversation_position": position
        }
    }


def export_training_data(
    config: dict,
    encryption_key_b64: str,
    min_affinity: int = 10
) -> tuple[bytes, int]:
    """
    Full training data export pipeline.
    
    1. Queries conversations with affinity >= min_affinity
    2. Pairs user/assistant messages within each conversation
    3. Formats each pair as an Alpaca example
    4. Serializes to JSON bytes
    5. Encrypts with AES-256-GCM
    6. Logs the export in training_export_log
    
    Args:
        config: Configuration dictionary
        encryption_key_b64: Base64-encoded AES-256 encryption key
        min_affinity: Minimum affinity threshold for inclusion (default 10)
        
    Returns:
        Tuple of (encrypted_bytes, example_count)
    """
    # Step 1: Query qualifying conversations
    conversations = database.get_conversations_for_export(min_affinity=min_affinity)
    
    # Step 2-3: Pair messages and format as Alpaca examples
    examples = []
    
    for conv_data in conversations:
        messages = conv_data["messages"]
        affinity = conv_data["affinity"]
        
        # Determine stage from affinity
        from wendy import get_stage
        stage_info = get_stage(affinity, config)
        stage_label = stage_info["label"]
        
        # Pair consecutive user/assistant messages
        position = 0
        for i in range(len(messages)):
            if messages[i]["role"] == "user":
                # Find the next assistant message
                for j in range(i + 1, len(messages)):
                    if messages[j]["role"] == "assistant":
                        example = format_alpaca_example(
                            user_msg=messages[i]["content"],
                            assistant_msg=messages[j]["content"],
                            affinity_stage=stage_label,
                            affinity_value=affinity,
                            position=position
                        )
                        examples.append(example)
                        position += 1
                        break
    
    # Step 4: Serialize to JSON bytes
    json_bytes = json.dumps(examples, indent=2, ensure_ascii=False).encode("utf-8")
    
    # Step 5: Encrypt
    encrypted = encrypt_data(json_bytes, encryption_key_b64)
    
    # Step 6: Log the export
    today = datetime.utcnow().strftime("%Y-%m-%d")
    export_format = config.get("training_export", {}).get("export_format", "alpaca")
    min_stage = config.get("training_export", {}).get("min_stage_for_export", "Acquaintance")
    
    database.log_training_export(
        export_date=today,
        count=len(examples),
        min_stage=min_stage,
        filename=f"training_{today}.enc",
        format=export_format
    )
    
    return encrypted, len(examples)
