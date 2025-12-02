"""
TrendMaster Agent API Blueprint
RESTful API a Desktop Agent-ek számára

Végpontok:
- POST /api/agent/register     - Agent regisztráció
- POST /api/agent/get-task     - Következő task lekérése
- POST /api/agent/task-status  - Task státusz jelentés
- POST /api/agent/heartbeat    - Életjel
- POST /api/agent/platform     - Platform fiók hozzáadása
- GET  /api/agent/stats        - Agent statisztikák
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime
import json

# Import SaaS database
from database_saas import saas_db, TaskStatus, TaskType, Platform


# ═══════════════════════════════════════════════════════════════════════════
# BLUEPRINT SETUP
# ═══════════════════════════════════════════════════════════════════════════
agent_api = Blueprint('agent_api', __name__, url_prefix='/api/agent')


# ═══════════════════════════════════════════════════════════════════════════
# AUTH DECORATOR
# ═══════════════════════════════════════════════════════════════════════════

def require_api_key(f):
    """
    Decorator: API kulcs validálás.
    Header: X-API-Key: tm_xxxxx
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.json.get('api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key required',
                'code': 'AUTH_MISSING'
            }), 401
        
        user = saas_db.get_user_by_api_key(api_key)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'code': 'AUTH_INVALID'
            }), 401
        
        # Add user to request context
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated


# ═══════════════════════════════════════════════════════════════════════════
# AGENT REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/register', methods=['POST'])
@require_api_key
def register_agent():
    """
    Register new agent for user.
    
    POST body:
    {
        "name": "My Desktop Agent",
        "hwid_hash": "sha256_of_hwid",
        "version": "2.0.0",
        "capabilities": ["facebook", "instagram"]
    }
    
    Response:
    {
        "success": true,
        "agent_id": "agent_xxxx",
        "name": "My Desktop Agent",
        "status": "online"
    }
    """
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({
            'success': False,
            'error': 'Agent name required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    user = request.current_user
    
    result = saas_db.register_agent(
        user_id=user['id'],
        name=data.get('name'),
        hwid_hash=data.get('hwid_hash'),
        version=data.get('version', '2.0.0'),
        capabilities=data.get('capabilities')
    )
    
    if result:
        print(f"✅ Agent registered: {result['agent_id']} for user {user['email']}")
        return jsonify({
            'success': True,
            **result
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Registration failed',
            'code': 'REGISTRATION_ERROR'
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# GET TASK
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/get-task', methods=['POST'])
@require_api_key
def get_task():
    """
    Get next available task for agent.
    
    POST body:
    {
        "agent_id": "agent_xxxx",
        "platforms": ["facebook", "instagram"],
        "version": "2.0.0"
    }
    
    Response (has task):
    {
        "success": true,
        "has_task": true,
        "task": {
            "id": "task_xxxx",
            "platform": "facebook",
            "task_type": "post",
            "content": "Post content...",
            "media_urls": [],
            "target_url": null
        }
    }
    
    Response (no task):
    {
        "success": true,
        "has_task": false
    }
    """
    data = request.get_json()
    
    agent_id = data.get('agent_id')
    platforms = data.get('platforms', [])
    
    if not agent_id:
        return jsonify({
            'success': False,
            'error': 'Agent ID required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    if not platforms:
        return jsonify({
            'success': False,
            'error': 'At least one platform required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate agent belongs to user
    agent = saas_db.get_agent(agent_id)
    if not agent or agent['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Agent not found or unauthorized',
            'code': 'AGENT_NOT_FOUND'
        }), 404
    
    # Update heartbeat
    saas_db.update_agent_heartbeat(agent_id, platforms)
    
    # Get next task
    task = saas_db.get_next_task(agent_id, platforms)
    
    if task:
        # Parse media_urls JSON
        try:
            task['media_urls'] = json.loads(task.get('media_urls', '[]'))
        except:
            task['media_urls'] = []
        
        return jsonify({
            'success': True,
            'has_task': True,
            'task': {
                'id': task['id'],
                'platform': task['platform'],
                'task_type': task['task_type'],
                'content': task.get('content'),
                'media_urls': task['media_urls'],
                'target_url': task.get('target_url'),
                'priority': task.get('priority', 5)
            }
        })
    else:
        return jsonify({
            'success': True,
            'has_task': False
        })


# ═══════════════════════════════════════════════════════════════════════════
# TASK STATUS UPDATE
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/task-status', methods=['POST'])
@require_api_key
def update_task_status():
    """
    Update task execution status.
    
    POST body:
    {
        "agent_id": "agent_xxxx",
        "task_id": "task_xxxx",
        "status": "completed|failed|in_progress",
        "error": "Error message if failed",
        "result": "Optional result data"
    }
    
    Response:
    {
        "success": true,
        "task_id": "task_xxxx",
        "status": "completed"
    }
    """
    data = request.get_json()
    
    agent_id = data.get('agent_id')
    task_id = data.get('task_id')
    status = data.get('status')
    error_message = data.get('error')
    result = data.get('result')
    
    if not all([agent_id, task_id, status]):
        return jsonify({
            'success': False,
            'error': 'agent_id, task_id, and status required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate status
    valid_statuses = ['in_progress', 'completed', 'failed']
    if status not in valid_statuses:
        return jsonify({
            'success': False,
            'error': f'Invalid status. Must be one of: {valid_statuses}',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate agent
    agent = saas_db.get_agent(agent_id)
    if not agent or agent['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Agent not found or unauthorized',
            'code': 'AGENT_NOT_FOUND'
        }), 404
    
    # Validate task
    task = saas_db.get_task(task_id)
    if not task or task['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Task not found or unauthorized',
            'code': 'TASK_NOT_FOUND'
        }), 404
    
    # Update status
    success = saas_db.update_task_status(
        task_id=task_id,
        status=status,
        agent_id=agent_id,
        error_message=error_message,
        result=result
    )
    
    if success:
        print(f"📋 Task {task_id} status: {status}")
        
        # Auto-retry on failure if retries available
        if status == 'failed' and task.get('retry_count', 0) < task.get('max_retries', 3):
            saas_db.retry_failed_task(task_id)
            print(f"🔄 Task {task_id} queued for retry")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': status
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to update task status',
            'code': 'UPDATE_ERROR'
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# HEARTBEAT
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/heartbeat', methods=['POST'])
@require_api_key
def heartbeat():
    """
    Agent heartbeat - keeps agent online status.
    
    POST body:
    {
        "agent_id": "agent_xxxx",
        "platforms": ["facebook", "instagram"],
        "version": "2.0.0",
        "stats": {
            "tasks_completed": 10,
            "uptime_minutes": 120
        }
    }
    
    Response:
    {
        "success": true,
        "server_time": "2025-01-01T12:00:00",
        "pending_tasks": 5
    }
    """
    data = request.get_json()
    
    agent_id = data.get('agent_id')
    platforms = data.get('platforms', [])
    
    if not agent_id:
        return jsonify({
            'success': False,
            'error': 'Agent ID required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate agent
    agent = saas_db.get_agent(agent_id)
    if not agent or agent['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Agent not found or unauthorized',
            'code': 'AGENT_NOT_FOUND'
        }), 404
    
    # Update heartbeat
    saas_db.update_agent_heartbeat(agent_id, platforms)
    
    # Count pending tasks for user
    user_tasks = saas_db.get_user_tasks(request.current_user['id'], status='pending')
    
    return jsonify({
        'success': True,
        'server_time': datetime.now().isoformat(),
        'pending_tasks': len(user_tasks)
    })


# ═══════════════════════════════════════════════════════════════════════════
# PLATFORM ACCOUNT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/platform', methods=['POST'])
@require_api_key
def add_platform():
    """
    Add platform account to agent.
    
    POST body:
    {
        "agent_id": "agent_xxxx",
        "platform": "facebook",
        "account_name": "John Doe"
    }
    
    Response:
    {
        "success": true,
        "account_id": "acc_xxxx",
        "platform": "facebook",
        "account_name": "John Doe"
    }
    """
    data = request.get_json()
    
    agent_id = data.get('agent_id')
    platform = data.get('platform')
    account_name = data.get('account_name')
    
    if not all([agent_id, platform, account_name]):
        return jsonify({
            'success': False,
            'error': 'agent_id, platform, and account_name required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate platform
    valid_platforms = ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']
    if platform.lower() not in valid_platforms:
        return jsonify({
            'success': False,
            'error': f'Invalid platform. Must be one of: {valid_platforms}',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate agent
    agent = saas_db.get_agent(agent_id)
    if not agent or agent['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Agent not found or unauthorized',
            'code': 'AGENT_NOT_FOUND'
        }), 404
    
    # Add platform
    result = saas_db.add_platform_account(
        user_id=request.current_user['id'],
        agent_id=agent_id,
        platform=platform.lower(),
        account_name=account_name
    )
    
    if result:
        print(f"✅ Platform added: {platform} ({account_name}) to agent {agent_id}")
        return jsonify({
            'success': True,
            **result
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Platform already exists or failed to add',
            'code': 'ADD_ERROR'
        }), 400


@agent_api.route('/platforms/<agent_id>', methods=['GET'])
@require_api_key
def get_platforms(agent_id):
    """
    Get all platform accounts for agent.
    
    Response:
    {
        "success": true,
        "platforms": [
            {"id": "acc_xxx", "platform": "facebook", "account_name": "John"}
        ]
    }
    """
    # Validate agent
    agent = saas_db.get_agent(agent_id)
    if not agent or agent['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Agent not found or unauthorized',
            'code': 'AGENT_NOT_FOUND'
        }), 404
    
    platforms = saas_db.get_agent_platforms(agent_id)
    
    return jsonify({
        'success': True,
        'platforms': platforms
    })


# ═══════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    """
    Get user statistics (agents, tasks, etc.)
    
    Response:
    {
        "success": true,
        "stats": {
            "agents": {"total": 2, "online": 1},
            "tasks": {"total": 100, "completed": 90, "failed": 5, "pending": 5},
            "accounts": {"total": 3}
        }
    }
    """
    user = request.current_user
    stats = saas_db.get_user_stats(user['id'])
    
    return jsonify({
        'success': True,
        'stats': stats
    })


@agent_api.route('/agents', methods=['GET'])
@require_api_key
def list_agents():
    """
    List all agents for user.
    
    Response:
    {
        "success": true,
        "agents": [
            {"id": "agent_xxx", "name": "My Agent", "status": "online", ...}
        ]
    }
    """
    user = request.current_user
    agents = saas_db.get_user_agents(user['id'])
    
    return jsonify({
        'success': True,
        'agents': agents
    })


# ═══════════════════════════════════════════════════════════════════════════
# TASK CREATION (from web dashboard)
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/create-task', methods=['POST'])
@require_api_key
def create_task():
    """
    Create new task (usually from web dashboard).
    
    POST body:
    {
        "platform": "facebook",
        "task_type": "post",
        "content": "Hello World!",
        "media_urls": ["https://..."],
        "scheduled_at": "2025-01-01T12:00:00",
        "priority": 5
    }
    
    Response:
    {
        "success": true,
        "task_id": "task_xxxx",
        "status": "pending"
    }
    """
    data = request.get_json()
    
    platform = data.get('platform')
    task_type = data.get('task_type')
    
    if not platform or not task_type:
        return jsonify({
            'success': False,
            'error': 'platform and task_type required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate platform
    valid_platforms = ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']
    if platform.lower() not in valid_platforms:
        return jsonify({
            'success': False,
            'error': f'Invalid platform',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Validate task type
    valid_types = ['post', 'like', 'comment', 'share', 'story']
    if task_type.lower() not in valid_types:
        return jsonify({
            'success': False,
            'error': f'Invalid task type',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    user = request.current_user
    
    result = saas_db.create_task(
        user_id=user['id'],
        platform=platform.lower(),
        task_type=task_type.lower(),
        content=data.get('content'),
        target_url=data.get('target_url'),
        media_urls=data.get('media_urls'),
        scheduled_at=data.get('scheduled_at'),
        priority=data.get('priority', 5)
    )
    
    if result:
        print(f"📋 Task created: {result['task_id']} ({task_type} on {platform})")
        return jsonify({
            'success': True,
            **result
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to create task',
            'code': 'CREATE_ERROR'
        }), 500


@agent_api.route('/tasks', methods=['GET'])
@require_api_key
def list_tasks():
    """
    List tasks for user.
    
    Query params:
    - status: filter by status (pending, completed, failed, etc.)
    - limit: max results (default 50)
    
    Response:
    {
        "success": true,
        "tasks": [...]
    }
    """
    user = request.current_user
    status = request.args.get('status')
    limit = int(request.args.get('limit', 50))
    
    tasks = saas_db.get_user_tasks(user['id'], status=status, limit=limit)
    
    # Parse media_urls JSON
    for task in tasks:
        try:
            task['media_urls'] = json.loads(task.get('media_urls', '[]'))
        except:
            task['media_urls'] = []
    
    return jsonify({
        'success': True,
        'tasks': tasks,
        'count': len(tasks)
    })


@agent_api.route('/task/<task_id>/logs', methods=['GET'])
@require_api_key
def get_task_logs(task_id):
    """
    Get execution logs for task.
    
    Response:
    {
        "success": true,
        "logs": [...]
    }
    """
    # Validate task belongs to user
    task = saas_db.get_task(task_id)
    if not task or task['user_id'] != request.current_user['id']:
        return jsonify({
            'success': False,
            'error': 'Task not found',
            'code': 'NOT_FOUND'
        }), 404
    
    logs = saas_db.get_task_logs(task_id)
    
    return jsonify({
        'success': True,
        'logs': logs
    })


# ═══════════════════════════════════════════════════════════════════════════
# USER REGISTRATION (simple version)
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.route('/user/register', methods=['POST'])
def register_user():
    """
    Register new user (SaaS signup).
    
    POST body:
    {
        "email": "user@example.com",
        "password": "securepassword",
        "name": "John Doe"
    }
    
    Response:
    {
        "success": true,
        "user_id": "xxx",
        "api_key": "tm_xxxx"
    }
    """
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'error': 'Email and password required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    if len(password) < 8:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 8 characters',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    result = saas_db.create_user(email, password, name)
    
    if result:
        print(f"✅ User registered: {email}")
        return jsonify({
            'success': True,
            'user_id': result['id'],
            'email': result['email'],
            'api_key': result['api_key']
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Email already exists',
            'code': 'DUPLICATE_EMAIL'
        }), 400


@agent_api.route('/user/login', methods=['POST'])
def login_user():
    """
    Login user (get API key).
    
    POST body:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    
    Response:
    {
        "success": true,
        "api_key": "tm_xxxx"
    }
    """
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'error': 'Email and password required',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    user = saas_db.verify_user(email, password)
    
    if user:
        return jsonify({
            'success': True,
            'user_id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'api_key': user['api_key']
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid email or password',
            'code': 'AUTH_FAILED'
        }), 401


# ═══════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

@agent_api.errorhandler(400)
def bad_request(e):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'code': 'BAD_REQUEST'
    }), 400


@agent_api.errorhandler(500)
def server_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'SERVER_ERROR'
    }), 500
