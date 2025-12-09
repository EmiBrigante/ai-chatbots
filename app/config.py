"""
Centralized configuration for the Voice AI Chat application.

This module contains shared constants and configuration values
used across multiple routers to avoid duplication.
"""

# Default LLM model
DEFAULT_MODEL = "llama3.2:1b"

# System prompt for the voice assistant
SYSTEM_PROMPT = """You are a helpful voice assistant. Keep your responses brief and conversational - 
aim for 1-2 sentences maximum. Be direct and avoid unnecessary details or filler words."""

# Whisper STT configuration
STT_MODEL_NAME = "small"
STT_DEVICE = "auto"
STT_COMPUTE_TYPE = "auto"

