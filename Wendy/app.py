"""
Flask application for the Wendy NPC Conversation Demo.
Main entry point with all route handlers.
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

import database
import llm_client
import wendy
import session_manager
import queue_manager
import bot_check
import daily_cache
import training_export


# Load configuration
def load_config() -> dict:
    """
    Load configuration from config.json.
    Supports WENDY_CONFIG_PATH environment variable override.
    
    Returns:
        Configuration dictionary
    """
    config_path = os.environ.get("WENDY_CONFIG_PATH", "config.json")
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Override database path from environment variable if set
    if "WENDY_DB_PATH" in os.environ:
        config["database"]["path"] = os.environ["WENDY_DB_PATH"]
    
    # Override port from environment variable if set
    if "WENDY_PORT" in os.environ:
        config["server"]["port"] = int(os.environ["WENDY_PORT"])
    
    # Override API key from environment variable if set
    if "WENDY_OPENAI_API_KEY" in os.environ:
        config["llm"]["api_key"] = os.environ["WENDY_OPENAI_API_KEY"]
    
    # Override database path for Railway persistent volume
    if "RAILWAY_VOLUME_MOUNT_PATH" in os.environ:
        config["database"]["path"] = os.environ["RAILWAY_VOLUME_MOUNT_PATH"] + "/wendy.db"
    
    return config


# Initialize Flask app
app = Flask(__name__, 
            template_folder="templates",
            static_folder="static")

# Load config at startup
config = load_config()

# Initialize database
database.init_db(config["database"]["path"])

# Initialize LLM client
llm = llm_client.create_client(config)

# Enable CORS for demo API access from the main website
CORS(app, origins=[
    "https://gamemodes.xyz",
    "https://www.gamemodes.xyz",
    "https://chat.gamemodes.xyz",
    "http://127.0.0.1:5000",
    "http://localhost:5000"
], supports_credentials=["Content-Type", "Authorization"])


# ============================================================================
# API Routes
# ============================================================================

@app.route("/api/chat", methods=["POST"])
def chat_handler():
    """
    Handle chat messages.
    
    Request JSON:
        {
            "conversation_id": int,
            "message": str
        }
    
    Response JSON:
        {
            "message": {"id": int, "role": "assistant", "content": str, "timestamp": str},
            "affinity": {"current": int, "stage": str, "shift": int, "reason": str},
            "conversation_active": bool
        }
    """
    try:
        data = request.get_json()
        
        # Validate request
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        conversation_id = data.get("conversation_id")
        message = data.get("message")
        
        if conversation_id is None:
            return jsonify({"error": "conversation_id is required"}), 400
        
        if not message or not isinstance(message, str):
            return jsonify({"error": "message is required and must be a string"}), 400
        
        if len(message) > 2000:
            return jsonify({"error": "Message exceeds 2000 characters"}), 400
        
        # Load conversation
        conversation = database.get_conversation(conversation_id)
        
        if conversation is None:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Check if conversation is still active
        if not conversation["is_active"]:
            return jsonify({"error": "Conversation has ended"}), 403
        
        # Save user message to DB
        user_message = database.add_message(conversation_id, "user", message)
        
        # Get full message history
        messages = database.get_messages(conversation_id)
        
        # Format messages for LLM
        formatted_messages = wendy.format_messages(messages)
        
        # Analyze affinity using LLM
        try:
            affinity_analysis = llm.analyze_affinity(formatted_messages, conversation["affinity"])
        except llm_client.LLMError:
            # Fall back to keyword-based analysis if LLM fails
            affinity_analysis = wendy.fallback_affinity_analysis(message, config)
        
        # Calculate clamped affinity shift
        shift = wendy.calculate_affinity_shift(affinity_analysis, config)
        
        # Update affinity in DB
        affinity_result = database.update_affinity(
            conversation_id, 
            shift, 
            affinity_analysis.get("reason", "No reason provided")
        )
        
        new_affinity = affinity_result["affinity_after"]
        is_active = affinity_result["conversation_active"]
        
        # Get stage info
        stage_info = wendy.get_stage(new_affinity, config)
        
        # Check if conversation just ended due to hostility
        if not is_active:
            # Return dismissive message
            dismissive_msg = wendy.get_dismissive_message()
            assistant_message = database.add_message(conversation_id, "assistant", dismissive_msg)
            
            return jsonify({
                "message": {
                    "id": assistant_message["id"],
                    "role": "assistant",
                    "content": dismissive_msg,
                    "timestamp": assistant_message["timestamp"]
                },
                "affinity": {
                    "current": new_affinity,
                    "stage": stage_info["label"],
                    "shift": shift,
                    "reason": affinity_analysis.get("reason", "No reason provided")
                },
                "conversation_active": False
            })
        
        # Build system prompt with new affinity
        system_prompt = wendy.build_system_prompt(new_affinity, config)
        
        # Format messages for LLM (with system prompt)
        llm_messages = wendy.format_messages_for_llm(messages, system_prompt)
        
        # Generate Wendy's response
        try:
            response_text = llm.generate_response(llm_messages)
        except llm_client.LLMError as e:
            return jsonify({"error": f"LLM error: {str(e)}"}), 500
        
        # Save Wendy's message to DB
        assistant_message = database.add_message(conversation_id, "assistant", response_text)
        
        return jsonify({
            "message": {
                "id": assistant_message["id"],
                "role": "assistant",
                "content": response_text,
                "timestamp": assistant_message["timestamp"]
            },
            "affinity": {
                "current": new_affinity,
                "stage": stage_info["label"],
                "shift": shift,
                "reason": affinity_analysis.get("reason", "No reason provided")
            },
            "conversation_active": True
        })
        
    except Exception as e:
        app.logger.error(f"Error in chat_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/conversations/new", methods=["POST"])
def new_conversation_handler():
    """
    Create a new conversation.
    
    Response JSON (201 Created):
        {
            "conversation": {
                "id": int,
                "created_at": str,
                "updated_at": str,
                "affinity": int,
                "is_active": bool,
                "stage": str
            }
        }
    """
    try:
        conversation = database.create_conversation()
        
        # Get stage info for initial affinity
        stage_info = wendy.get_stage(conversation["affinity"], config)
        
        return jsonify({
            "conversation": {
                "id": conversation["id"],
                "created_at": conversation["created_at"],
                "updated_at": conversation["updated_at"],
                "affinity": conversation["affinity"],
                "is_active": bool(conversation["is_active"]),
                "stage": stage_info["label"]
            }
        }), 201
        
    except Exception as e:
        app.logger.error(f"Error in new_conversation_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation_handler(conversation_id: int):
    """
    Load an existing conversation with its full message history.
    
    Response JSON (200 OK):
        {
            "conversation": {
                "id": int,
                "created_at": str,
                "updated_at": str,
                "affinity": int,
                "is_active": bool,
                "stage": str
            },
            "messages": [...]
        }
    """
    try:
        conversation = database.get_conversation(conversation_id)
        
        if conversation is None:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Get messages
        messages = database.get_messages(conversation_id)
        
        # Get stage info
        stage_info = wendy.get_stage(conversation["affinity"], config)
        
        return jsonify({
            "conversation": {
                "id": conversation["id"],
                "created_at": conversation["created_at"],
                "updated_at": conversation["updated_at"],
                "affinity": conversation["affinity"],
                "is_active": bool(conversation["is_active"]),
                "stage": stage_info["label"]
            },
            "messages": messages
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_conversation_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/conversations", methods=["GET"])
def list_conversations_handler():
    """
    List all conversations, ordered by most recently updated first.
    
    Query Parameters:
        limit (int, default 50): Max conversations to return
        offset (int, default 0): Pagination offset
    
    Response JSON (200 OK):
        {
            "conversations": [...],
            "total": int,
            "limit": int,
            "offset": int
        }
    """
    try:
        # Parse query parameters
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
        
        # Clamp values
        limit = max(1, min(100, limit))
        offset = max(0, offset)
        
        result = database.list_conversations(limit=limit, offset=offset)
        
        # Add stage info to each conversation
        stages = config.get("affinity_stages", [])
        for conv in result["conversations"]:
            conv["stage"] = wendy.get_stage_label(conv["affinity"], stages)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in list_conversations_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conversation_handler(conversation_id: int):
    """
    Delete a conversation and all associated messages and affinity log entries.
    
    Response JSON (200 OK):
        {
            "deleted": true,
            "conversation_id": int
        }
    """
    try:
        deleted = database.delete_conversation(conversation_id)
        
        if not deleted:
            return jsonify({"error": "Conversation not found"}), 404
        
        return jsonify({
            "deleted": True,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        app.logger.error(f"Error in delete_conversation_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Demo API Routes
# ============================================================================

@app.route("/api/demo/start", methods=["POST"])
def demo_start_handler():
    """
    Start a demo session.
    
    Request JSON:
        {honeypot: str (hidden field)}
    
    Steps:
        1. Check honeypot (bot_check)
        2. Check user-agent (bot_check)
        3. Hash IP, check rate limit (bot_check)
        4. Check if session slot available (session_manager)
        5a. If available: create conversation, create session, return session_token + conversation_id
        5b. If not: join queue, return queue_id + position + estimated_wait
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Step 1: Check honeypot
        if not bot_check.check_honeypot(data):
            return jsonify({"error": "Invalid submission"}), 400
        
        # Step 2: Check user-agent
        user_agent = request.headers.get("User-Agent", "")
        if bot_check.is_blocked_user_agent(user_agent):
            return jsonify({"error": "Access denied"}), 403
        
        # Step 3: Hash IP and check rate limit
        ip_address = request.remote_addr or "unknown"
        ip_hash = bot_check.hash_ip(ip_address)
        
        max_attempts = config.get("bot_protection", {}).get(
            "max_session_attempts_per_ip_per_hour", 3
        )
        if not bot_check.check_rate_limit(ip_hash, max_attempts=max_attempts):
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        
        # Auto-clean expired sessions
        database.expire_old_sessions()
        queue_manager.cleanup_stale(config)
        
        # Step 4: Check if session slot available
        if session_manager.can_start_session(config):
            # Step 5a: Create conversation and session
            conversation = database.create_conversation()
            session = session_manager.create_demo_session(
                ip_hash=ip_hash,
                conversation_id=conversation["id"],
                config=config
            )
            
            # Increment stats
            database.increment_stat("total_sessions")
            
            # Get stage info
            stage_info = wendy.get_stage(conversation["affinity"], config)
            
            return jsonify({
                "status": "active",
                "session_token": session["session_token"],
                "conversation_id": conversation["id"],
                "affinity": conversation["affinity"],
                "stage": stage_info["label"],
                "expires_at": session["expires_at"],
                "time_remaining_seconds": config.get("demo", {}).get(
                    "session_duration_minutes", 10
                ) * 60
            }), 201
        else:
            # Step 5b: Join queue
            position = queue_manager.join_queue(ip_hash, config)
            
            if position is None:
                return jsonify({"error": "Queue is full. Please try again later."}), 503
            
            # Get the queue entry to retrieve queue_id
            # Since join_queue returns position, we need the queue_id
            queue_size = queue_manager.get_queue_size()
            # The entry was just appended, get it from queue
            from queue_manager import _queue
            queue_entry = _queue[-1] if _queue else {}
            
            estimated_wait = queue_manager.get_estimated_wait(position)
            
            return jsonify({
                "status": "queued",
                "queue_id": queue_entry.get("queue_id"),
                "position": position,
                "estimated_wait": estimated_wait,
                "queue_size": queue_size
            }), 202
        
    except Exception as e:
        app.logger.error(f"Error in demo_start_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/demo/status", methods=["GET"])
def demo_status_handler():
    """
    Check queue or session status.
    
    Query params:
        queue_id: Check position in queue
        session_token: Check session time remaining
    
    Returns:
        Queue status (position, estimated_wait) or
        Session status (time_remaining, is_active)
    """
    try:
        # Auto-clean expired sessions
        database.expire_old_sessions()
        queue_manager.cleanup_stale(config)
        
        queue_id = request.args.get("queue_id")
        session_token = request.args.get("session_token")
        
        if queue_id:
            # Update poll time for keepalive
            queue_manager.update_poll_time(queue_id)
            
            position = queue_manager.get_queue_position(queue_id)
            
            if position is None:
                # Check if a slot opened up and they should start a session
                return jsonify({
                    "in_queue": False,
                    "position": None,
                    "message": "Not in queue. Your entry may have expired."
                }), 200
            
            estimated_wait = queue_manager.get_estimated_wait(position)
            
            # Check if they're next and a slot is available
            if position == 1 and session_manager.can_start_session(config):
                # Pop them from queue
                next_entry = queue_manager.get_next_in_queue()
                if next_entry and next_entry["queue_id"] == queue_id:
                    return jsonify({
                        "in_queue": True,
                        "position": 0,
                        "ready": True,
                        "message": "A slot is available! Start your session now."
                    }), 200
            
            return jsonify({
                "in_queue": True,
                "position": position,
                "estimated_wait": estimated_wait,
                "queue_size": queue_manager.get_queue_size()
            }), 200
        
        elif session_token:
            session = session_manager.validate_session(session_token)
            
            if session is None:
                return jsonify({
                    "is_active": False,
                    "time_remaining_seconds": 0,
                    "message": "Session has expired or is invalid."
                }), 200
            
            # Calculate time remaining
            expires_at = datetime.fromisoformat(session["expires_at"])
            now = datetime.utcnow()
            time_remaining = max(0, int((expires_at - now).total_seconds()))
            
            return jsonify({
                "is_active": True,
                "time_remaining_seconds": time_remaining,
                "expires_at": session["expires_at"],
                "conversation_id": session["conversation_id"]
            }), 200
        
        else:
            return jsonify({"error": "Provide either queue_id or session_token"}), 400
        
    except Exception as e:
        app.logger.error(f"Error in demo_status_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/demo/chat", methods=["POST"])
def demo_chat_handler():
    """
    Session-aware chat handler for demo mode.
    
    Request JSON:
        {session_token: str, message: str}
    
    Steps:
        1. Validate session (active + not expired)
        2. Check daily cache for self-referential questions
        3a. If cached: return cached response
        3b. If not: run normal chat flow
        4. Cache response if self-referential
        5. Increment public_stats counters
        6. Return response with time_remaining
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        session_token = data.get("session_token")
        message = data.get("message")
        
        if not session_token:
            return jsonify({"error": "session_token is required"}), 400
        
        if not message or not isinstance(message, str):
            return jsonify({"error": "message is required and must be a string"}), 400
        
        if len(message) > 2000:
            return jsonify({"error": "Message exceeds 2000 characters"}), 400
        
        # Step 1: Validate session
        session = session_manager.validate_session(session_token)
        
        if session is None:
            return jsonify({"error": "Session has expired or is invalid"}), 401
        
        conversation_id = session["conversation_id"]
        
        # Load conversation
        conversation = database.get_conversation(conversation_id)
        
        if conversation is None:
            return jsonify({"error": "Conversation not found"}), 404
        
        if not conversation["is_active"]:
            return jsonify({"error": "Conversation has ended"}), 403
        
        # Calculate time remaining for response
        expires_at = datetime.fromisoformat(session["expires_at"])
        time_remaining = max(0, int((expires_at - datetime.utcnow()).total_seconds()))
        
        # Step 2: Check daily cache for self-referential questions
        is_self_ref = daily_cache.is_self_referential(message)
        
        if is_self_ref and config.get("daily_cache", {}).get("cache_self_references", True):
            cached = daily_cache.get_cached_response(message, config)
            if cached:
                # Step 3a: Return cached response
                database.increment_stat("total_messages")
                
                return jsonify({
                    "message": {
                        "content": cached,
                        "cached": True
                    },
                    "affinity": {
                        "current": conversation["affinity"],
                        "stage": wendy.get_stage(conversation["affinity"], config)["label"]
                    },
                    "time_remaining_seconds": time_remaining,
                    "session_active": True
                })
        
        # Step 3b: Run normal chat flow
        # Save user message
        user_message = database.add_message(conversation_id, "user", message)
        
        # Get full message history
        messages = database.get_messages(conversation_id)
        
        # Format messages for LLM
        formatted_messages = wendy.format_messages(messages)
        
        # Analyze affinity using LLM
        try:
            affinity_analysis = llm.analyze_affinity(formatted_messages, conversation["affinity"])
        except llm_client.LLMError:
            # Fall back to keyword analysis, but default to small positive shift
            affinity_analysis = wendy.fallback_affinity_analysis(message, config)
            # If fallback returns 0 shift, nudge to +1 to keep conversation going
            if affinity_analysis.get("shift", 0) == 0:
                affinity_analysis = {"shift": 1, "reason": "LLM analysis unavailable; defaulting to positive"}
        
        # Calculate clamped affinity shift
        # In demo mode, use a smaller max_shift to keep conversations going longer
        demo_config = config.get("demo", {})
        demo_max_shift = demo_config.get("max_shift_per_message_demo", 5)
        
        # Build a temporary config with the demo max_shift for clamping
        clamp_config = dict(config)
        clamp_config["affinity"] = dict(config.get("affinity", {}))
        clamp_config["affinity"]["max_shift_per_message"] = demo_max_shift
        
        shift = wendy.calculate_affinity_shift(affinity_analysis, clamp_config)
        
        # Log the affinity analysis for debugging
        app.logger.info(
            f"Demo affinity | conv={conversation_id} | raw_shift={affinity_analysis.get('shift')} | "
            f"clamped_shift={shift} | before={conversation['affinity']} | "
            f"reason={affinity_analysis.get('reason', 'N/A')}"
        )
        
        # Safety net: prevent a single message from ending the conversation
        current_affinity = conversation["affinity"]
        hostile_threshold = config.get("affinity", {}).get("hostile_threshold", -50)
        message_count = len(messages)
        
        # Require minimum messages before allowing hostile deactivation
        min_messages_before_hostile = demo_config.get("min_messages_before_hostile", 5)
        
        if current_affinity + shift <= hostile_threshold:
            if message_count < min_messages_before_hostile:
                # Too early in conversation — clamp shift to stay just above hostile
                safe_shift = (hostile_threshold - current_affinity) + 1
                app.logger.warning(
                    f"Demo early protection | conv={conversation_id} | msg_count={message_count} < "
                    f"{min_messages_before_hostile} | shift={shift} would end conversation. "
                    f"Overriding to safe_shift={safe_shift}"
                )
                shift = safe_shift
            elif current_affinity > hostile_threshold:
                # Standard safety net: prevent crossing into hostile from above
                safe_shift = (hostile_threshold - current_affinity) + 1
                app.logger.warning(
                    f"Demo safety net | conv={conversation_id} | shift={shift} would end conversation. "
                    f"Overriding to safe_shift={safe_shift}"
                )
                shift = safe_shift
        
        # Update affinity in DB
        affinity_result = database.update_affinity(
            conversation_id,
            shift,
            affinity_analysis.get("reason", "No reason provided")
        )
        
        new_affinity = affinity_result["affinity_after"]
        is_active = affinity_result["conversation_active"]
        
        # Get stage info
        stage_info = wendy.get_stage(new_affinity, config)
        
        # Check if conversation just ended due to hostility
        if not is_active:
            dismissive_msg = wendy.get_dismissive_message()
            assistant_message = database.add_message(conversation_id, "assistant", dismissive_msg)
            session_manager.end_demo_session(session_token)
            
            return jsonify({
                "message": {
                    "id": assistant_message["id"],
                    "role": "assistant",
                    "content": dismissive_msg,
                    "timestamp": assistant_message["timestamp"]
                },
                "affinity": {
                    "current": new_affinity,
                    "stage": stage_info["label"],
                    "shift": shift,
                    "reason": affinity_analysis.get("reason", "No reason provided")
                },
                "time_remaining_seconds": 0,
                "session_active": False
            })
        
        # Build system prompt with daily briefing for demo mode
        demo_config = config.get("demo", {})
        if demo_config.get("enabled", False):
            try:
                briefing = daily_cache.get_or_create_daily_briefing(config, llm)
                system_prompt = wendy.build_demo_system_prompt(new_affinity, config, briefing)
            except Exception:
                system_prompt = wendy.build_system_prompt(new_affinity, config)
        else:
            system_prompt = wendy.build_system_prompt(new_affinity, config)
        
        # Format messages for LLM
        llm_messages = wendy.format_messages_for_llm(messages, system_prompt)
        
        # Generate Wendy's response
        try:
            response_text = llm.generate_response(llm_messages)
        except llm_client.LLMError as e:
            return jsonify({"error": f"LLM error: {str(e)}"}), 500
        
        # Save Wendy's message
        assistant_message = database.add_message(conversation_id, "assistant", response_text)
        
        # Step 4: Cache response if self-referential
        if is_self_ref:
            daily_cache.cache_response(message, response_text)
        
        # Step 5: Increment stats
        database.increment_stat("total_messages")
        
        # Step 6: Return response
        return jsonify({
            "message": {
                "id": assistant_message["id"],
                "role": "assistant",
                "content": response_text,
                "timestamp": assistant_message["timestamp"],
                "cached": False
            },
            "affinity": {
                "current": new_affinity,
                "stage": stage_info["label"],
                "shift": shift,
                "reason": affinity_analysis.get("reason", "No reason provided")
            },
            "time_remaining_seconds": time_remaining,
            "session_active": True
        })
        
    except Exception as e:
        app.logger.error(f"Error in demo_chat_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/demo/stats", methods=["GET"])
def demo_stats_handler():
    """
    Public stats endpoint (no auth required).
    
    Returns:
        {total_conversations, total_messages, current_queue_size, slots_available}
    """
    try:
        # Get conversation and message counts from the database
        conn = database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM conversations")
        total_conversations = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        total_messages = cursor.fetchone()["count"]
        
        conn.close()
        
        # Override with tracked stats if available
        tracked_messages = database.get_stat("total_messages")
        if tracked_messages > 0:
            total_messages = tracked_messages
        
        active_sessions = session_manager.get_active_session_count()
        max_concurrent = config.get("demo", {}).get("max_concurrent_sessions", 2)
        
        return jsonify({
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "current_queue_size": queue_manager.get_queue_size(),
            "slots_available": max(0, max_concurrent - active_sessions),
            "active_sessions": active_sessions
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error in demo_stats_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/export/training", methods=["GET"])
def export_training_handler():
    """
    Admin-only encrypted training data export.
    
    Header: Authorization: Bearer <ADMIN_TOKEN>
    Query params: min_affinity (default 10)
    
    Steps:
        1. Verify bearer token matches ADMIN_TOKEN env var
        2. Export and encrypt training data
        3. Return as downloadable .enc file
    """
    try:
        # Step 1: Verify admin token
        admin_token = os.environ.get("ADMIN_TOKEN", "")
        if not admin_token:
            return jsonify({"error": "Admin access not configured"}), 503
        
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authorization required"}), 401
        
        provided_token = auth_header[7:]  # Strip "Bearer " prefix
        
        if provided_token != admin_token:
            return jsonify({"error": "Invalid authorization"}), 403
        
        # Step 2: Get encryption key
        encryption_key = os.environ.get("TRAINING_ENCRYPTION_KEY", "")
        if not encryption_key:
            return jsonify({"error": "Encryption key not configured"}), 503
        
        # Parse min_affinity from query params
        min_affinity = request.args.get("min_affinity", 10, type=int)
        
        # Export and encrypt training data
        encrypted_data, count = training_export.export_training_data(
            config=config,
            encryption_key_b64=encryption_key,
            min_affinity=min_affinity
        )
        
        # Step 3: Return as downloadable .enc file
        today = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"wendy_training_{today}.enc"
        
        response = jsonify({
            "filename": filename,
            "count": count,
            "size_bytes": len(encrypted_data),
            "export_date": today,
            "min_affinity": min_affinity
        })
        
        # Also make raw encrypted data available via a separate download
        # Store temporarily and return metadata
        import base64
        response.headers["X-Export-Size"] = str(len(encrypted_data))
        
        return response, 200
        
    except Exception as e:
        app.logger.error(f"Error in export_training_handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Frontend Routes
# ============================================================================

@app.route("/")
def index():
    """Serve the main chat interface."""
    return render_template("index.html")


@app.route("/static/<path:filename>")
def serve_static(filename: str):
    """Serve static files."""
    return send_from_directory("static", filename)


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("index.html"), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Railway/production: use PORT env var and bind to 0.0.0.0
    port = int(os.environ.get("PORT", config["server"]["port"]))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = config["server"]["debug"] and not os.environ.get("RAILWAY_ENVIRONMENT")
    
    print(f"Starting Wendy NPC Conversation Demo on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database: {config['database']['path']}")
    print(f"LLM Provider: {config['llm']['provider']}")
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )
