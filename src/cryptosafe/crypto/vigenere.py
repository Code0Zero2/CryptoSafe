"""Vigenère Cipher implementation for educational classical layer."""

import re
from cryptosafe.common.errors import ValidationError

def clean_key(key: str) -> str:
    """Validate and normalize Vigenère keyword to uppercase alphabetic characters."""
    if not key or not isinstance(key, str):
        raise ValidationError("Kunci Vigenère tidak boleh kosong.")
    
    sanitized = re.sub(r"[^A-Za-z]", "", key).upper()
    if not sanitized:
        raise ValidationError("Kunci Vigenère harus memuat setidaknya satu karakter huruf alfabet (A-Z).")
    return sanitized

def vigenere_encrypt(plaintext: str, key: str) -> str:
    """Encrypt plaintext using the Vigenère cipher.

    Case is preserved. Non-alphabetic characters (spaces, punctuation, digits,
    Unicode) remain unchanged and do not advance the key index.
    """
    if not plaintext:
        return ""

    sanitized_key = clean_key(key)
    key_len = len(sanitized_key)
    key_shifts = [ord(c) - ord("A") for c in sanitized_key]

    result = []
    key_idx = 0

    for ch in plaintext:
        if "A" <= ch <= "Z":
            shift = key_shifts[key_idx % key_len]
            enc_char = chr((ord(ch) - ord("A") + shift) % 26 + ord("A"))
            result.append(enc_char)
            key_idx += 1
        elif "a" <= ch <= "z":
            shift = key_shifts[key_idx % key_len]
            enc_char = chr((ord(ch) - ord("a") + shift) % 26 + ord("a"))
            result.append(enc_char)
            key_idx += 1
        else:
            result.append(ch)

    return "".join(result)

def vigenere_decrypt(ciphertext: str, key: str) -> str:
    """Decrypt ciphertext using the Vigenère cipher.

    Reverses the key shift while preserving non-alphabetic characters and casing.
    """
    if not ciphertext:
        return ""

    sanitized_key = clean_key(key)
    key_len = len(sanitized_key)
    key_shifts = [ord(c) - ord("A") for c in sanitized_key]

    result = []
    key_idx = 0

    for ch in ciphertext:
        if "A" <= ch <= "Z":
            shift = key_shifts[key_idx % key_len]
            dec_char = chr((ord(ch) - ord("A") - shift) % 26 + ord("A"))
            result.append(dec_char)
            key_idx += 1
        elif "a" <= ch <= "z":
            shift = key_shifts[key_idx % key_len]
            dec_char = chr((ord(ch) - ord("a") - shift) % 26 + ord("a"))
            result.append(dec_char)
            key_idx += 1
        else:
            result.append(ch)

    return "".join(result)

