import pytest
from unittest.mock import patch
import time
import json
from typing import Dict
from zerotrace.core.messenger_core import SecureMessenger
from zerotrace.core.utils import b64_enc


@pytest.fixture
def secure_messenger():
    """Create SecureMessenger instance with generated keys"""
    messenger = SecureMessenger()
    messenger.generate_keys()
    return messenger

@pytest.fixture
def secure_messenger_client():
    """Create SecureMessenger instance with generated keys"""
    messenger = SecureMessenger()
    messenger.generate_keys()
    return messenger

def test_generate_keys(secure_messenger):
    """Test key generation"""
    kem_pub, sig_pub = secure_messenger.generate_keys()
    
    assert kem_pub
    assert sig_pub
    assert secure_messenger.kem_public_key == kem_pub
    assert secure_messenger.signature_public_key == sig_pub

def test_save_load_keys(secure_messenger):
    """Test saving and loading keys"""
    password = b"test_password"
    
    # Save keys
    key_bundle = secure_messenger.save_keys(password)
    assert isinstance(key_bundle, dict)
    assert "salt" in key_bundle
    assert "nonce" in key_bundle
    assert "public_keys" in key_bundle
    assert "encrypted_keys" in key_bundle
    
    # Load keys
    success = secure_messenger.load_keys(key_bundle, password)
    assert success is True

def test_load_keys_wrong_password(secure_messenger):
    """Test loading keys with wrong password"""
    key_bundle = secure_messenger.save_keys(b"correct_password")
    success = secure_messenger.load_keys(key_bundle, b"wrong_password")
    assert success is False

def test_send_message(secure_messenger):
    """Test sending message"""
    recipient_key = b"recipient_pub_key"
    message = b"test message"
    timestamp = time.time()

    result = secure_messenger.encrypt_message(
        recipient_key, message, timestamp
    )

    assert result

def test_encrypt_decrypt_message(secure_messenger, secure_messenger_client):
    """Test message decryption"""
    message: bytes = b"Hello World"
    result = secure_messenger.encrypt_message(
        secure_messenger_client.kem_public_key, message, 0
    )
    print(  result)
    result = secure_messenger_client.decrypt_message(result)
    print(  result)
    assert isinstance(result, dict)
    assert "sender_id" in result
    assert "message" in result
    assert "timestamp" in result

def test_full_message_flow():
    """Integration test for full message flow"""
    # Create two messenger instances
    sender = SecureMessenger()
    receiver = SecureMessenger()
    
    # Generate keys for both
    sender.generate_keys()
    receiver_pub_key, _ = receiver.generate_keys()
    
    # Send message
    message = b"integration test message"
    timestamp = time.time()
    
    success = sender.encrypt_message(
        receiver_pub_key, message, timestamp
    )
    result = receiver.decrypt_message(success)
    assert result

def test_key_persistence(tmp_path):
    """Integration test for key persistence"""
    messenger = SecureMessenger()
    messenger.generate_keys()
    
    password = b"test_password"
    key_bundle = messenger.save_keys(password)
    
    # Create new instance and load keys
    new_messenger = SecureMessenger()
    success = new_messenger.load_keys(key_bundle, password)
    
    assert success is True
    assert new_messenger.kem_public_key == messenger.kem_public_key
    assert new_messenger.signature_public_key == messenger.signature_public_key