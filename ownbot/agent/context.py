from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from ownbot.skills import SkillLoader


class ContextBuilder:
    """
    Builds context for LLM calls by combining session history, system prompts, and current input.
    
    Implements ReAct (Reasoning + Acting) architecture for better complex task handling.
    """

    _RUNTIME_CONTEXT_TAG = "[runtime-context]"

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.skill_loader = SkillLoader()
        self._load_skills()
    
    def _load_skills(self) -> None:
        """Load all available skills."""
        self.skill_loader.load_all_skills()
    
    def reload_skills(self) -> None:
        """Reload all skills (useful for hot-reloading)."""
        self._load_skills()
    
    def get_skill_system_prompt(self) -> str:
        """Get system prompt additions from loaded skills."""
        return self.skill_loader.get_system_prompt_additions()

    def build_messages(
        self,
        history: List[dict[str, Any]],
        current_message: str,
        media: Optional[List[str]] = None,
        channel: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> List[dict[str, Any]]:
        """
        Build a list of messages for the LLM using ReAct architecture.
        
        Args:
            history: Previous messages in the session.
            current_message: The current user message.
            media: Optional list of media file paths.
            channel: The channel the message came from.
            chat_id: The chat ID.
        
        Returns:
            A list of message dicts for the LLM.
        """
        messages: List[dict[str, Any]] = []

        # ReAct System prompt - 严格要求格式
        system_prompt = """You are OwnBot, a helpful AI assistant using ReAct (Reasoning + Acting) architecture.

Your goal is to provide accurate and useful responses to user queries by thinking step by step.

IMPORTANT: You must ALWAYS use the following exact format for your responses:

Thought: [Your thinking process here]

Then either:
1. If you need to use a tool:
   Action: [tool_name]
   Action Input: [JSON parameters]

2. If you have the final answer:
   Final Answer: [Your response to the user]

Rules:
- ALWAYS start with "Thought:"
- When giving final answer, ALWAYS use "Final Answer:" prefix
- Never output both Action and Final Answer in the same response
- Be concise and helpful in your Final Answer
- Do not include the thought process in the Final Answer

Example 1 (using tool):
Thought: The user wants to know the weather in Tokyo. I need to use the web_request tool to get this information.
Action: web_request
Action Input: {"url": "https://api.weather.com/tokyo", "method": "GET"}

Example 2 (final answer):
Thought: I have successfully retrieved the weather information for Tokyo.
Final Answer: The weather in Tokyo is 22°C and sunny today.

Guidelines:
- Always think before acting
- Be concise in your thoughts
- Only use tools when necessary
- If you're unsure, ask for clarification
- Respect user privacy
"""
        
        # Add skills to system prompt
        skills_prompt = self.get_skill_system_prompt()
        if skills_prompt:
            system_prompt += skills_prompt
        
        messages.append({"role": "system", "content": system_prompt.strip()})

        # Add history
        messages.extend(history)

        # Add current message
        user_content: Any = current_message
        if media:
            user_content = []
            user_content.append({"type": "text", "text": current_message})
            for m in media:
                # For simplicity, assume images; could be extended
                user_content.append({"type": "image_url", "image_url": {"url": m}})

        messages.append({"role": "user", "content": user_content})

        return messages

    def add_assistant_message(
        self,
        messages: List[dict[str, Any]],
        content: Optional[str],
        tool_calls: Optional[List[dict[str, Any]]] = None,
        reasoning_content: Optional[str] = None,
    ) -> List[dict[str, Any]]:
        """Add an assistant message to the context."""
        msg: dict[str, Any] = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        messages.append(msg)
        return messages

    def add_tool_result(
        self,
        messages: List[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> List[dict[str, Any]]:
        """Add a tool result as an observation to the context."""
        # Format as ReAct observation
        observation_content = f"Observation: {result}"
        
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": observation_content,
        }
        messages.append(tool_message)
        return messages

    def parse_react_response(self, content: str) -> dict[str, Any]:
        """
        Parse a ReAct formatted response.
        
        Returns:
            dict with keys: 'thought', 'action', 'action_input', 'final_answer'
        """
        result = {
            'thought': None,
            'action': None,
            'action_input': None,
            'final_answer': None,
        }
        
        if not content:
            return result
        
        # Parse Thought - look for "Thought:" at the beginning
        thought_match = self._extract_thought(content)
        if thought_match:
            result['thought'] = thought_match
        
        # Parse Action
        action_match = self._extract_section(content, 'Action')
        if action_match:
            result['action'] = action_match.strip()
        
        # Parse Action Input
        action_input_match = self._extract_section(content, 'Action Input')
        if action_input_match:
            result['action_input'] = action_input_match.strip()
        
        # Parse Final Answer - try multiple patterns
        final_answer = self._extract_final_answer(content)
        if final_answer:
            result['final_answer'] = final_answer
        
        return result
    
    def _extract_thought(self, content: str) -> Optional[str]:
        """Extract thought section - handles multiple Thought: occurrences."""
        import re
        
        if not content:
            return None
        
        # Normalize content: remove extra whitespace and newlines
        normalized = content.strip()
        
        # Pattern 1: Look for Thought: at the start or after newlines
        # Match until Action:, Final Answer:, or end of content
        pattern = r'(?:^|\n)\s*Thought:\s*(.*?)(?=\n\s*(?:Action:|Final Answer:|$))'
        match = re.search(pattern, normalized, re.DOTALL | re.IGNORECASE)
        
        if match:
            thought = match.group(1).strip()
            if thought and not thought.isspace():
                return thought
        
        # Pattern 2: More lenient - just find Thought: and get everything after it
        # until a line starting with a word followed by colon
        pattern2 = r'Thought:\s*(.+?)(?=\n[A-Za-z_]+:|$)'
        match2 = re.search(pattern2, normalized, re.DOTALL | re.IGNORECASE)
        if match2:
            thought = match2.group(1).strip()
            if thought and not thought.isspace():
                return thought
        
        # Pattern 3: If content starts with non-formatted text that looks like a thought
        # (first sentence or first line)
        if 'Thought:' not in content and 'Action:' not in content and 'Final Answer:' not in content:
            lines = content.strip().split('\n')
            first_line = lines[0].strip()
            if first_line and len(first_line) > 10:
                return first_line[:200]  # Return first line as thought preview
        
        return None
    
    def _extract_final_answer(self, content: str) -> Optional[str]:
        """Extract final answer using multiple patterns."""
        import re
        
        if not content:
            return None
        
        normalized = content.strip()
        
        # Pattern 1: "Final Answer:" followed by content (case insensitive)
        pattern1 = r'(?:^|\n)\s*Final Answer:\s*(.*?)(?=\n[A-Za-z_]+:|$)'
        match1 = re.search(pattern1, normalized, re.DOTALL | re.IGNORECASE)
        if match1:
            answer = match1.group(1).strip()
            if answer:
                return answer
        
        # Pattern 2: "**Final Answer**:" markdown format
        pattern2 = r'\*\*Final Answer\*\*:\s*(.*?)(?=\n[A-Za-z_]+:|$)'
        match2 = re.search(pattern2, normalized, re.DOTALL | re.IGNORECASE)
        if match2:
            answer = match2.group(1).strip()
            if answer:
                return answer
        
        # Pattern 3: If no explicit marker but has Thought and no Action, 
        # treat everything after the last Thought as the answer
        if 'Thought:' in normalized and 'Action:' not in normalized:
            # Find the last Thought: and extract everything after it
            last_thought_idx = normalized.rfind('Thought:')
            if last_thought_idx != -1:
                after_thought = normalized[last_thought_idx + len('Thought:'):].strip()
                # Remove any leading newlines
                after_thought = after_thought.lstrip('\n')
                if after_thought:
                    return after_thought
        
        # Pattern 4: If no markers at all, return the whole content as answer
        # (for non-ReAct formatted responses)
        if 'Thought:' not in normalized and 'Action:' not in normalized and 'Final Answer:' not in normalized:
            return normalized
        
        return None
    
    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a section from ReAct formatted content."""
        import re
        
        if not content:
            return None
        
        # Match section name followed by colon and content until next section or end
        # Use word boundary to avoid partial matches
        pattern = rf'(?:^|\n)\s*{section_name}:\s*(.*?)(?=\n[A-Za-z_]+:|$)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            result = match.group(1).strip()
            if result:
                return result
        return None
