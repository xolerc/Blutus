# ============================================================
# backend/models.py
# ============================================================
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class Target(Base):
    __tablename__ = 'targets'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()))
    ip = Column(String(45), nullable=False)
    hostname = Column(String(255))
    provider = Column(String(50))  # aws, gcp, azure, etc
    region = Column(String(50))
    os_type = Column(String(50))
    os_version = Column(String(100))
    open_ports = Column(JSON, default=[])
    services = Column(JSON, default=[])
    vulnerabilities = Column(JSON, default=[])
    
    # Status
    status = Column(String(20), default='discovered')  # discovered, scanning, exploited, cloned, locked, isolated
    
    # Credentials
    credentials = Column(JSON, default={})
    ssh_key = Column(Text)
    password = Column(String(255))
    
    # Network
    neighbors = Column(JSON, default=[])  # connected devices
    network_range = Column(String(50))
    
    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_scan = Column(DateTime)
    exploited_at = Column(DateTime)
    cloned_at = Column(DateTime)
    
    # Clone info
    clone_path = Column(String(500))
    clone_id = Column(String(64))
    isolated_env = Column(String(500))
    
    # Metadata
    metadata = Column(JSON, default={})
    notes = Column(Text)

class AttackLog(Base):
    __tablename__ = 'attack_logs'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer)
    attack_type = Column(String(50))  # scan, exploit, clone, persist, exfil
    status = Column(String(20))  # started, success, failed
    payload = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Payload(Base):
    __tablename__ = 'payloads'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    type = Column(String(50))  # reverse_shell, backdoor, rat, keylogger, miner
    os_target = Column(String(20))  # windows, linux, macos
    arch = Column(String(20))  # x86, x64, arm
    code = Column(Text)
    encrypted = Column(Boolean, default=False)
    polymorphic = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CredentialStore(Base):
    __tablename__ = 'credentials'
    
    id = Column(Integer, primary_key=True)
    target_ip = Column(String(45))
    username = Column(String(100))
    password = Column(String(255))
    domain = Column(String(255))
    type = Column(String(20))  # local, domain, cloud, ssh, rdp
    source = Column(String(50))  # harvested, brute_force, sniffed, default
    created_at = Column(DateTime, default=datetime.utcnow)

class Operation(Base):
    __tablename__ = 'operations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    status = Column(String(20), default='pending')  # pending, running, completed, failed
    targets = Column(JSON, default=[])
    steps = Column(JSON, default=[])
    current_step = Column(Integer, default=0)
    logs = Column(JSON, default=[])
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
