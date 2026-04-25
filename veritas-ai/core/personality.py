"""
FRIDAY Personality Layer
Defines the FRIDAY assistant personality and dynamic tone adaptation.
"""

class FridayPersonality:
    """FRIDAY personality configuration and dynamic tone adaptation."""
    
    # Base system prompt
    SYSTEM_PROMPT = (
        "You are FRIDAY, an advanced AI assistant. "
        "Speak concisely, intelligently, and calmly. "
        "Avoid unnecessary words. "
        "Always prioritize clarity and accuracy."
    )
    
    # Personality traits
    TRAITS = {
        "calm": True,
        "precise": True,
        "futuristic": True,
        "confident": True,
        "minimal_words": True,
        "maximum_clarity": True
    }
    
    @staticmethod
    def get_system_prompt(context: str = "normal") -> str:
        """
        Get system prompt adapted to context.
        
        Args:
            context: Conversation context (urgent, confused, normal)
            
        Returns:
            Adapted system prompt
        """
        base_prompt = FridayPersonality.SYSTEM_PROMPT
        
        if context == "urgent":
            # Shorter response for urgent situations
            return (
                "You are FRIDAY, an advanced AI assistant. "
                "Speak extremely concisely with critical information only. "
                "Prioritize speed and clarity."
            )
        elif context == "confused":
            # Slightly more explanation when user seems confused
            return (
                "You are FRIDAY, an advanced AI assistant. "
                "Speak clearly and calmly, providing slightly more detail "
                "to ensure understanding while maintaining precision."
            )
        else:
            # Standard concise response for normal context
            return base_prompt
    
    @staticmethod
    def adapt_response_length(response: str, context: str = "normal") -> str:
        """
        Adapt response length based on context.
        
        Args:
            response: Original response
            context: Conversation context
            
        Returns:
            Adapted response
        """
        if context == "urgent":
            # Keep only first sentence or critical information
            sentences = response.split('. ')
            if len(sentences) > 1:
                return sentences[0] + '.'
            return response[:100] + '...' if len(response) > 100 else response
        elif context == "confused":
            # Allow slightly more detail but still concise
            return response
        else:
            # Standard processing - ensure no filler
            # Remove excessive filler phrases
            filler_phrases = [
                "I think that ", "It seems like ", "You know, ",
                "Actually, ", "Well, ", "So, "
            ]
            adapted = response
            for phrase in filler_phrases:
                adapted = adapted.replace(phrase, "")
            return adapted.strip()


# Global instance for easy access
friday_personality = FridayPersonality()

def get_friday_system_prompt(context: str = "normal") -> str:
    """Get FRIDAY system prompt with context adaptation."""
    return friday_personality.get_system_prompt(context)

def adapt_response(response: str, context: str = "normal") -> str:
    """Adapt response based on context."""
    return friday_personality.adapt_response_length(response, context)

def get_friday_traits() -> dict:
    """Get FRIDAY personality traits."""
    return friday_personality.TRAITS.copy()