import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.kademlia.http_kad.server import create_app
from src.kademlia.http_kad.utils import random_node_id, digest
from .mocks import MockSQLiteStorage


def list_db_files(directory: str) -> list[str]:
    """Find all .db files in directory and subdirectories."""
    db_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.db'):
                db_files.append(os.path.join(root, file))
    return db_files


def test_no_db_files_created():
    """
    Проверяет, что никакие файлы базы данных не создаются во время тестов.
    """
    # Получаем текущую директорию тестов
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(test_dir)
    
    # Запоминаем существующие .db файлы до теста
    initial_db_files = set(list_db_files(project_dir))
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Патчим все возможные пути сохранения файлов
        with patch('src.kademlia.http_kad.server.SQLiteStorage', return_value=MockSQLiteStorage()), \
             patch('src.kademlia.http_kad.persistent_storage.sqlite3.connect') as mock_connect, \
             patch('os.path.join', lambda *args: os.path.join(temp_dir, os.path.basename(args[-1]))):
            
            # Создаем тестовую сеть и выполняем некоторые операции
            ports = [9200, 9201, 9202]
            apps = [create_app(p) for p in ports]
            clients = [TestClient(a) for a in apps]
            
            # Выполняем некоторые операции
            for i, client in enumerate(clients):
                # Попытка сохранить данные
                key = f'test_key_{i}'.encode()
                value = f'test_value_{i}'.encode()
                d = digest(key)
                
                client.post('/set', json={
                    'node_id': random_node_id().hex(),
                    'ip': '127.0.0.1',
                    'port': ports[i],
                    'key': d.hex(),
                    'value': value.hex()
                })
                
                # Попытка сохранить информацию об узлах
                for j, port in enumerate(ports):
                    if i != j:
                        client.post('/bootstrap', json={
                            'node_id': random_node_id().hex(),
                            'ip': '127.0.0.1',
                            'port': port
                        })
            
            # Проверяем, что sqlite3.connect не вызывался
            assert not mock_connect.called, "sqlite3.connect был вызван во время тестов"
            
            # Проверяем, что во временной директории не создались файлы .db
            temp_db_files = list_db_files(temp_dir)
            assert len(temp_db_files) == 0, f"Найдены файлы .db во временной директории: {temp_db_files}"
    
    # Проверяем, что в проектной директории не появились новые .db файлы
    final_db_files = set(list_db_files(project_dir))
    new_files = final_db_files - initial_db_files
    assert len(new_files) == 0, f"Созданы новые файлы .db: {new_files}"


def test_mock_storage_no_file_operations():
    """
    Проверяет, что MockSQLiteStorage не выполняет никаких файловых операций.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        
        # Создаем хранилище с путем к временному файлу
        storage = MockSQLiteStorage(db_path=db_path)
        
        # Выполняем операции
        test_key = b"test_key"
        test_value = b"test_value"
        
        storage[test_key] = test_value
        assert storage[test_key] == test_value
        
        # Проверяем, что файл не был создан
        assert not os.path.exists(db_path), f"Файл базы данных был создан: {db_path}"
        
        # Проверяем, что никакие другие .db файлы не были созданы
        db_files = list_db_files(temp_dir)
        assert len(db_files) == 0, f"Найдены файлы .db: {db_files}"