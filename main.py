# meditation_api/main.py

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging
import uuid
import os
import shutil
from datetime import datetime
import time 

from GoogleApiCall import GoogleApiCall
# from voice_service import MeditationVoiceService  # COMMENTED OUT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Meditation API", version="1.0.0")

# Add CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
google_ai = GoogleApiCall()
# voice_service = MeditationVoiceService(preferred_voice="aoede")  # COMMENTED OUT

# Pydantic models for request/response
class CheckinData(BaseModel):
    agitation: Optional[int] = 3  # 1-5 scale
    energy: Optional[str] = "normal"  # sleepy/normal/wired
    emotions: Optional[List[str]] = []  # anger, stress, joy, etc.
    preference: Optional[str] = "auto"  # breath_focus, body_scan, loving_kindness, auto

class IntroductionRequest(BaseModel):
    meditation_type: str
    duration_minutes: int
    user_profile: Optional[str] = ""
    checkin_data: Optional[CheckinData] = None

class IntroductionResponse(BaseModel):
    session_id: str
    introduction_text: str
    audio_url: str

def create_session_folder():
    """Create a new session folder"""
    session_id = f"session_{int(datetime.now().timestamp())}"
    session_path = f"audio/sessions/{session_id}"
    
    os.makedirs(session_path, exist_ok=True)
    
    # Clean up old sessions (keep only last 5)
    cleanup_old_sessions()
    
    return session_id, session_path

def cleanup_old_sessions():
    """Keep only the 5 most recent session folders"""
    sessions_dir = "audio/sessions"
    if not os.path.exists(sessions_dir):
        return
    
    sessions = [d for d in os.listdir(sessions_dir) 
                if os.path.isdir(os.path.join(sessions_dir, d))]
    sessions.sort(reverse=True)  # Most recent first
    
    # Remove old sessions beyond the 5 most recent
    for old_session in sessions[5:]:
        old_path = os.path.join(sessions_dir, old_session)
        shutil.rmtree(old_path)
        logger.info(f"Cleaned up old session: {old_session}")

@app.post("/api/meditation/introduction", response_model=IntroductionResponse)
async def create_meditation_introduction(request: IntroductionRequest):
    """Generate personalized meditation introduction with audio"""
    start_time = time.time()
    
    try:
        logger.info(f"Creating introduction for {request.meditation_type}, {request.duration_minutes} minutes")
        
        # Create session folder
        session_id, session_path = create_session_folder()
        
        # Generate text (this works)
        text_start = time.time()
        context = _build_introduction_context(request)
        introduction_text = _generate_introduction_text(context)
        text_duration = time.time() - text_start
        logger.info(f"Text generation took: {text_duration:.2f} seconds")
        
        # Try audio generation with fallback
        audio_url = ""
        # VOICE SERVICE TEMPORARILY DISABLED
        # try:
        #     audio_start = time.time()
        #     audio_bytes = voice_service.generate_audio(introduction_text)
        #     audio_duration = time.time() - audio_start
        #     logger.info(f"Audio generation took: {audio_duration:.2f} seconds")
        #     
        #     # Save in session folder
        #     audio_filename = "introduction.wav"
        #     audio_path = f"{session_path}/{audio_filename}"
        #     
        #     with open(audio_path, "wb") as f:
        #         f.write(audio_bytes)
        #     
        #     audio_url = f"/audio/sessions/{session_id}/{audio_filename}"
        #     
        # except Exception as audio_error:
        #     logger.warning(f"Audio generation failed: {audio_error}")
        #     logger.info("Continuing without audio")
        #     # Continue without audio
        
        total_duration = time.time() - start_time
        logger.info(f"Total request took: {total_duration:.2f} seconds")
        
        return IntroductionResponse(
            session_id=session_id,
            introduction_text=introduction_text,
            audio_url=audio_url  # Will be empty if audio failed
        )
        
    except Exception as e:
        logger.error(f"Error creating introduction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create introduction: {str(e)}")
    
def _build_introduction_context(request: IntroductionRequest) -> Dict:
    """Build context for AI introduction generation"""
    context = {
        "meditation_type": request.meditation_type,
        "duration_minutes": request.duration_minutes,
        "user_profile": request.user_profile or "New meditator",
    }
    
    if request.checkin_data:
        context.update({
            "agitation_level": request.checkin_data.agitation,
            "energy_level": request.checkin_data.energy,
            "current_emotions": request.checkin_data.emotions,
            "meditation_preference": request.checkin_data.preference
        })
    
    return context

def _generate_introduction_text(context: Dict) -> str:
    """Generate personalized introduction using Google AI"""
    # Build AI prompt
    prompt = f"""
You are a wise, experienced meditation teacher starting a session with a student.

STUDENT CONTEXT:
- Profile: {context.get('user_profile', 'New meditator')}
- Today's practice: {context['meditation_type']} for {context['duration_minutes']} minutes
- Current agitation level: {context.get('agitation_level', 'unknown')}/5
- Energy level: {context.get('energy_level', 'normal')}
- Present emotions: {context.get('current_emotions', [])}
- Preference: {context.get('meditation_preference', 'auto')}

INSTRUCTIONS:
Create a warm, personalized introduction (30-45 words) that:
1. Acknowledges their current state with compassion
2. Sets realistic expectations for the session
3. Gives initial settling guidance
4. Feels personal and encouraging

Be natural and authentic, not overly spiritual. Speak directly to them.

Examples of good tone:
- "I can sense you're carrying some stress today. That's exactly why we're here..."
- "Your mind seems quite active right now, which is perfectly normal..."
- "I notice you're feeling a bit low energy - let's work with that..."

Generate the introduction:
"""
    
    try:
        introduction = google_ai.generate_content(prompt)
        return introduction.strip()
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        # Fallback introduction
        return f"Welcome to your {context['duration_minutes']}-minute {context['meditation_type']} practice. Take a moment to settle in and let's begin this journey together."

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve audio files"""
    audio_path = f"audio/{filename}"
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    return Response(content=audio_data, media_type="audio/wav")

@app.get("/audio/sessions/{session_id}/{filename}")
async def get_session_audio(session_id: str, filename: str):
    """Serve session audio files"""
    audio_path = f"audio/sessions/{session_id}/{filename}"
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    return Response(content=audio_data, media_type="audio/wav")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Meditation API is running"}

# Test endpoint
@app.post("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {"message": "API is working!", "voice_service": "disabled"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)