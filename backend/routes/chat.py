from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import hashlib
from models.chat import (
    ChatMessage,
    ChatResponse,
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    QuizSubmissionRequest,
    QuizSubmissionResponse,
    QuizAnswer,
)
from services.rag_orchestrator import rag_orchestrator
from utils.logger import get_logger
from utils.logging_config import set_request_id, get_request_id, clear_request_id

logger = get_logger("chat_routes")

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_simple_user_id(request: Request) -> str:
    """
    Create a simple user ID based on client IP to isolate users.
    Each user gets their own chat history and PDF context.
    """
    client_ip = request.client.host if request.client else "unknown"
    # Create a simple hash of the IP for session isolation
    user_id = hashlib.md5(client_ip.encode()).hexdigest()[:12]
    return f"user_{user_id}"


class QuestionGenerationRequest(BaseModel):
    topic: Optional[str] = None
    count: Optional[int] = 25
    mode: Optional[str] = "practice"  # "quiz" for MCQ, "practice" for open-ended


@router.post("/", response_model=ChatResponse)
async def chat(message: ChatMessage, request: Request):
    """Send a message to the AI assistant - general chat with RAG context"""
    # Set request ID for tracing
    request_id = set_request_id()

    logger.info(
        f"Chat request received - endpoint: {'/api/chat'}, method: {'POST'}, user_agent: {request.headers.get('user-agent')}, content_length: {request.headers.get('content-length')}"
    )

    try:
        import datetime

        user_session = get_simple_user_id(request)

        # Use RAG orchestrator to get context and generate response
        result = await rag_orchestrator.query_and_generate(
            query=message.message,
            count=1,
            mode="chat",
            top_k=5,
            use_cache=True,
        )

        response = ChatResponse(
            response=result.get("response", "I couldn't generate a response."),
            timestamp=datetime.datetime.now().isoformat(),
        )

        logger.info(
            f"Chat request completed successfully - response_length: {len(response.response)}, timestamp: {response.timestamp}"
        )

        return response
    except Exception as e:
        logger.error(
            f"Chat request failed - error_type: {type(e).__name__}, error_message: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        clear_request_id()


@router.get("/history")
async def get_chat_history(request: Request):
    """Get the chat history for the current session"""
    user_session = get_simple_user_id(request)
    # Chat history is not implemented in the new RAG system yet
    return {"messages": [], "user_session": user_session}


@router.delete("/history")
async def clear_chat_history(request: Request):
    """Clear the chat history for the current session"""
    user_session = get_simple_user_id(request)
    # Chat history is not implemented in the new RAG system yet
    return {"status": "success", "message": "Chat history cleared"}


@router.post("/generate-questions", response_model=ChatResponse)
async def generate_questions(request: QuestionGenerationRequest, http_request: Request):
    """Generate Q&A questions from the selected PDF content, optionally focused on a specific topic"""
    # Set request ID for tracing
    request_id = set_request_id()

    logger.info(
        f"Question generation request received - endpoint: {'/api/chat/generate-questions'}, method: {'POST'}, topic: {request.topic}, count: {request.count}, mode: {request.mode}"
    )

    try:
        import datetime

        user_session = get_simple_user_id(http_request)

        # Use the new RAG orchestrator for question generation
        logger.info(f"Generating {request.count} questions using RAG orchestrator")

        # Build filter conditions based on user session if needed
        filter_conditions = None
        # Optionally filter by user's documents: {"user_session": user_session}

        result = await rag_orchestrator.query_and_generate(
            query=request.topic,
            count=request.count or 25,
            mode=request.mode or "practice",
            top_k=10,
            filter_conditions=filter_conditions,
            use_cache=True,
        )

        if result.get("success"):
            response = ChatResponse(
                response=result["response"],
                timestamp=datetime.datetime.now().isoformat(),
            )

            logger.info(
                f"Question generation completed successfully - response_length: {len(result['response'])}, questions_count: {request.count}"
            )

            return response
        else:
            error_message = result.get("error", "Failed to generate questions")
            logger.error(f"Question generation failed - error: {error_message}")
            raise HTTPException(status_code=500, detail=error_message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Question generation request failed - error_type: {type(e).__name__}, error_message: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        clear_request_id()


@router.post("/evaluate-answer", response_model=AnswerEvaluationResponse)
async def evaluate_answer(request: AnswerEvaluationRequest, http_request: Request):
    """Evaluate a single user answer using AI"""
    # This feature is not yet implemented in the new RAG system
    raise HTTPException(status_code=501, detail="Answer evaluation not implemented yet")


@router.post("/evaluate-quiz", response_model=QuizSubmissionResponse)
async def evaluate_quiz(request: QuizSubmissionRequest, http_request: Request):
    """Evaluate a complete quiz submission with overall feedback"""
    # This feature is not yet implemented in the new RAG system
    raise HTTPException(status_code=501, detail="Quiz evaluation not implemented yet")


@router.get("/performance-stats")
async def get_performance_stats():
    """Get current performance statistics and RAG system status"""
    try:
        # Get RAG system stats
        system_stats = await rag_orchestrator.get_system_stats()

        return {
            "status": "production_ready_rag_system",
            "rag_system": system_stats,
        }
    except Exception as e:
        logger.error(
            f"Failed to get performance stats: {str(e)}",
            extra={"extra_fields": {"error_type": type(e).__name__}},
        )
        return {
            "status": "error",
            "error": str(e),
        }
