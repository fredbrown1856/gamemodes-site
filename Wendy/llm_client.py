"""
LLM client module for the Wendy NPC Conversation Demo.
Provides an abstraction layer for LLM providers with OpenAI implementation.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Optional


class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass


class LLMClient(ABC):
    """Base class defining the LLM client interface."""

    def __init__(self, config: dict):
        """
        Initialize with config dict containing model settings.
        
        Args:
            config: Configuration dictionary with LLM settings
        """
        self.config = config

    @abstractmethod
    def generate_response(self, messages: list[dict]) -> str:
        """
        Send a list of chat messages to the LLM and return the assistant's response text.
        
        Args:
            messages: List of dicts with format [{"role": "system"|"user"|"assistant", "content": "..."}]
            
        Returns:
            String content of the assistant's reply
            
        Raises:
            LLMError on API failure
        """
        pass

    @abstractmethod
    def analyze_affinity(self, messages: list[dict], current_affinity: int) -> dict:
        """
        Ask the LLM to analyze the conversation and determine an affinity shift.
        
        Args:
            messages: List of conversation messages
            current_affinity: Current affinity value for context
            
        Returns:
            Dict with {"shift": int, "reason": str}
            
        Raises:
            LLMError on API failure
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API implementation of the LLM client."""

    def __init__(self, config: dict):
        """
        Initialize OpenAI-compatible client.
        
        Args:
            config: Config dict expecting keys: api_key, api_key_env, model, temperature, max_tokens, base_url (optional)
        """
        super().__init__(config)
        
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMError("openai package is not installed. Run: pip install openai")
        
        # Get API key from config or environment variable
        api_key = config.get("api_key", "")
        
        # If api_key not in config, check environment variables
        # api_key_env allows specifying which env var to check (for multi-provider setups)
        if not api_key:
            env_var = config.get("api_key_env", "WENDY_OPENAI_API_KEY")
            api_key = os.environ.get(env_var, "")
        
        # Fallback: check common env vars
        if not api_key:
            for env_var in ["WENDY_OPENAI_API_KEY", "OPENAI_API_KEY", "CEREBRAS_API_KEY"]:
                api_key = os.environ.get(env_var, "")
                if api_key:
                    break
        
        if not api_key:
            raise LLMError("API key not configured. Set WENDY_OPENAI_API_KEY (or OPENAI_API_KEY/CEREBRAS_API_KEY) environment variable or api_key in config.json")
        
        # Initialize OpenAI client
        base_url = config.get("base_url")
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)
        
        self.model = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.8)
        self.max_tokens = config.get("max_tokens", 300)
        
        # Affinity analysis settings (can use different model/temperature)
        self.affinity_model = config.get("affinity_model", self.model)
        self.affinity_temperature = config.get("affinity_temperature", 0.3)

    def generate_response(self, messages: list[dict]) -> str:
        """
        Call OpenAI Chat Completions API.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            Assistant's response text
            
        Raises:
            LLMError on API failure
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise LLMError(f"OpenAI API error in generate_response: {str(e)}")

    def analyze_affinity(self, messages: list[dict], current_affinity: int) -> dict:
        """
        Call OpenAI with a structured prompt to analyze affinity shift.
        
        Args:
            messages: List of conversation messages
            current_affinity: Current affinity value
            
        Returns:
            Dict with {"shift": int, "reason": str}
            
        Raises:
            LLMError on API failure
        """
        # Get the last 10 messages for context
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        # Format recent messages for the analysis prompt
        formatted_messages = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in recent_messages
        ])
        
        # Get the user's last message
        user_messages = [m for m in messages if m.get("role") == "user"]
        last_user_message = user_messages[-1]["content"] if user_messages else "No user message"
        
        analysis_prompt = f"""You are analyzing a conversation between a user and Wendy, an Appalachian NPC character.
Based on the user's most recent message and the conversation context, determine how
Wendy's emotional regard (affinity) toward the user would shift.

Current affinity: {current_affinity} (scale: -100 to 100)

Conversation (recent messages):
{formatted_messages}

User's last message: {last_user_message}

Respond with ONLY a JSON object (no other text):
{{
    "shift": <integer, typically -15 to +15>,
    "reason": "<brief explanation of the shift>"
}}

Consider:
- Warmth, respect, and genuine interest → positive shift
- Rudeness, insults, or dismissal → negative shift
- Shared values or personal connection → larger positive shift
- Threats or cruelty → larger negative shift
- Neutral small talk → small positive or zero shift"""

        try:
            response = self.client.chat.completions.create(
                model=self.affinity_model,
                messages=[
                    {"role": "system", "content": "You are an affinity analysis system. Respond only with valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.affinity_temperature,
                max_tokens=150
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON from the response
            # Handle cases where response might have markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Find JSON object in the response
            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                response_text = response_text[json_start:json_end]
            
            result = json.loads(response_text)
            
            # Validate the result
            shift = int(result.get("shift", 0))
            reason = str(result.get("reason", "No reason provided"))
            
            return {"shift": shift, "reason": reason}
            
        except json.JSONDecodeError:
            # JSON parsing failed — raise LLMError so caller falls back to keyword analysis
            import sys
            print(f"WARNING: Failed to parse affinity analysis JSON: {response_text!r}", file=sys.stderr)
            raise LLMError(f"Failed to parse affinity analysis response as JSON: {response_text[:200]}")
            
        except Exception as e:
            raise LLMError(f"OpenAI API error in analyze_affinity: {str(e)}")


class MockClient(LLMClient):
    """Mock LLM client for testing without API calls."""

    def __init__(self, config: dict):
        """Initialize mock client."""
        super().__init__(config)

    def generate_response(self, messages: list[dict]) -> str:
        """
        Return a mock response.
        
        Args:
            messages: List of message dicts (ignored)
            
        Returns:
            Mock response string
        """
        return "Well hey there! This is a mock response since the LLM ain't configured. Reckon you'll need to set up that API key if you want the real deal."

    def analyze_affinity(self, messages: list[dict], current_affinity: int) -> dict:
        """
        Return a mock affinity analysis.
        
        Args:
            messages: List of message dicts (ignored)
            current_affinity: Current affinity value (ignored)
            
        Returns:
            Dict with zero shift
        """
        return {"shift": 0, "reason": "Mock analysis - no actual analysis performed"}


def create_client(config: dict) -> LLMClient:
    """
    Factory function. Reads config['llm']['provider'] and returns
    the appropriate LLMClient subclass instance.
    
    If the specified provider fails to initialize (e.g., missing API key),
    automatically falls back to the MockClient for graceful degradation.
    
    Supported providers:
        - openai: OpenAI API (GPT models)
        - cerebras: Cerebras API (Llama models via OpenAI-compatible endpoint)
        - mock: Mock client for testing
    
    Args:
        config: Full configuration dictionary
        
    Returns:
        An LLMClient instance
        
    Raises:
        LLMError: If provider is not supported and fallback fails
    """
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "openai").lower()
    
    if provider == "mock":
        return MockClient(llm_config)
    elif provider == "openai":
        try:
            return OpenAIClient(llm_config)
        except LLMError as e:
            import sys
            print(f"WARNING: {e}", file=sys.stderr)
            print("WARNING: Falling back to MockClient. LLM responses will be simulated.", file=sys.stderr)
            return MockClient(llm_config)
    elif provider == "cerebras":
        # Cerebras uses an OpenAI-compatible API, so we reuse OpenAIClient
        # with Cerebras' defaults set
        try:
            cerebras_config = dict(llm_config)
            # Override with Cerebras-specific defaults
            cerebras_config["base_url"] = "https://api.cerebras.ai/v1"
            cerebras_config["model"] = cerebras_config.get("model", "llama3.1-8b")
            # Cerebras uses CEREBRAS_API_KEY env var by convention
            if not cerebras_config.get("api_key"):
                cerebras_config["api_key_env"] = cerebras_config.get("api_key_env", "CEREBRAS_API_KEY")
            return OpenAIClient(cerebras_config)
        except LLMError as e:
            import sys
            print(f"WARNING: {e}", file=sys.stderr)
            print("WARNING: Falling back to MockClient. LLM responses will be simulated.", file=sys.stderr)
            return MockClient(llm_config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}. Supported: openai, cerebras, mock")
