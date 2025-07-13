import pandas as pd
import logging
from typing import Dict, List, Optional
from GoogleApiCall import GoogleApiCall

class SessionPlanner:
    def __init__(self, csv_path: str = "phrase_list_with_audio.csv"):
        """Initialize session planner with phrase database"""
        self.csv_path = csv_path
        self.phrases_df = None
        self.google_ai = GoogleApiCall()
        self._load_phrases()
        
    def _load_phrases(self):
        """Load phrase database from CSV"""
        try:
            self.phrases_df = pd.read_csv(self.csv_path)
            logging.info(f"Loaded {len(self.phrases_df)} phrases from {self.csv_path}")
        except Exception as e:
            logging.error(f"Error loading phrases CSV: {e}")
            raise
    
    def get_available_phrases(self, meditation_type: str = "breath_focus") -> List[int]:
        """Get list of phrase IDs available for this meditation type"""
        return self.phrases_df.iloc[:, 0].tolist()  # First column is ID
    
    def create_session_plan(self, 
                          meditation_type: str,
                          duration_minutes: int,
                          user_context: Optional[Dict] = None) -> str:
        """Create personalized meditation session plan - returns CSV data"""
        
        # Get available phrases for this meditation type
        available_phrase_ids = self.get_available_phrases(meditation_type)
        
        # Build context for AI
        context = user_context or {}
        user_experience = context.get('experience_level', 'beginner')
        user_mood = context.get('mood', 'neutral')
        time_of_day = context.get('time_of_day', 'any')
        previous_pattern = context.get('previous_sessions', 'none')
        
        # Create AI prompt
        prompt = self._build_ai_prompt(
            meditation_type=meditation_type,
            duration_minutes=duration_minutes,
            user_experience=user_experience,
            user_mood=user_mood,
            time_of_day=time_of_day,
            previous_pattern=previous_pattern,
            available_phrase_ids=available_phrase_ids[:37]  # Only non-remembered phrases
        )
        
        try:
            # Get AI response - pure CSV
            csv_response = self.google_ai.generate_content(prompt)
            return csv_response.strip()
            
        except Exception as e:
            logging.error(f"Error creating session plan: {e}")
            # Simple fallback
            return self._create_default_csv(duration_minutes)
    
    def _build_ai_prompt(self, 
                        meditation_type: str,
                        duration_minutes: int,
                        user_experience: str,
                        user_mood: str,
                        time_of_day: str,
                        previous_pattern: str,
                        available_phrase_ids: List[int]) -> str:
        """Build the prompt for Google AI"""
        
        prompt = f"""
Create a {duration_minutes}-minute {meditation_type} session for a {user_experience} practitioner who is feeling {user_mood} in the {time_of_day}.

Available phrases: {available_phrase_ids}

Categories:
- 1-5: Opening (settling, initial breath awareness)
- 6-13: Basic breath awareness 
- 14-19: Deep breathing
- 20-25: Calming body/mind
- 26-31: Smiling/releasing
- 32-37: Present moment awareness

Select 6-10 phrases and return ONLY this format:
sequence,phrase_id,minute

Example:
1,1,0
2,6,2
3,14,5

Just the CSV data, nothing else.
"""
        
        return prompt
    
    def _create_default_csv(self, duration_minutes: int) -> str:
        """Simple fallback CSV"""
        if duration_minutes <= 10:
            return "1,1,0\n2,6,2\n3,14,5\n4,32,8"
        elif duration_minutes <= 20:
            return "1,1,0\n2,6,2\n3,14,5\n4,20,8\n5,26,12\n6,32,15"
        else:
            return "1,1,0\n2,6,3\n3,14,6\n4,20,10\n5,26,15\n6,32,20\n7,35,25"

# Test the session planner
if __name__ == "__main__":
    planner = SessionPlanner()
    
    # Test session creation
    csv_result = planner.create_session_plan(
        meditation_type="breath_focus",
        duration_minutes=15,
        user_context={
            "experience_level": "intermediate",
            "mood": "stressed",
            "time_of_day": "morning"
        }
    )
    
    print("Generated CSV session plan:")
    print(csv_result)
    