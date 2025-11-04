"""
Together AI Service for Lumina IQ RAG Backend.

Provides integration with Together AI API for LLM and embedding generation.
"""

from typing import List, Dict, Any, Optional
from together import Together
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("together_service")


class TogetherService:
    """Service for interacting with Together AI API."""

    def __init__(self):
        self.client: Optional[Together] = None
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize Together AI client."""
        try:
            if not settings.TOGETHER_API_KEY:
                logger.warning("TOGETHER_API_KEY not configured")
                return

            logger.info(
                "Initializing Together AI service",
                extra={
                    "extra_fields": {
                        "model": settings.TOGETHER_MODEL,
                        "embedding_model": settings.EMBEDDING_MODEL,
                    }
                },
            )

            self.client = Together(api_key=settings.TOGETHER_API_KEY)
            self.is_initialized = True

            logger.info("Together AI service initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize Together AI service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Together AI."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Together AI service not initialized")

        try:
            logger.debug(
                f"Generating embedding for text (length: {len(text)})",
                extra={"extra_fields": {"model": settings.EMBEDDING_MODEL}},
            )

            response = self.client.embeddings.create(
                input=text,
                model=settings.EMBEDDING_MODEL,
            )

            embedding = response.data[0].embedding

            logger.debug(
                f"Generated embedding successfully",
                extra={
                    "extra_fields": {
                        "embedding_dim": len(embedding),
                        "text_length": len(text),
                    }
                },
            )

            return embedding

        except Exception as e:
            logger.error(
                f"Failed to generate embedding: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "text_length": len(text),
                    }
                },
            )
            raise

    async def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Together AI service not initialized")

        try:
            logger.debug(
                f"Generating embeddings for batch",
                extra={
                    "extra_fields": {
                        "batch_size": len(texts),
                        "model": settings.EMBEDDING_MODEL,
                    }
                },
            )

            response = self.client.embeddings.create(
                input=texts,
                model=settings.EMBEDDING_MODEL,
            )

            embeddings = [item.embedding for item in response.data]

            logger.debug(
                f"Generated batch embeddings successfully",
                extra={
                    "extra_fields": {
                        "batch_size": len(embeddings),
                        "embedding_dim": len(embeddings[0]) if embeddings else 0,
                    }
                },
            )

            return embeddings

        except Exception as e:
            logger.error(
                f"Failed to generate batch embeddings: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "batch_size": len(texts),
                    }
                },
            )
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """Generate chat completion using Together AI."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Together AI service not initialized")

        try:
            logger.debug(
                "Generating chat completion",
                extra={
                    "extra_fields": {
                        "model": settings.TOGETHER_MODEL,
                        "message_count": len(messages),
                        "temperature": temperature,
                    }
                },
            )

            response = self.client.chat.completions.create(
                model=settings.TOGETHER_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )

            if stream:
                return response

            content = response.choices[0].message.content

            logger.debug(
                "Generated chat completion successfully",
                extra={
                    "extra_fields": {
                        "response_length": len(content),
                        "finish_reason": response.choices[0].finish_reason,
                    }
                },
            )

            return content

        except Exception as e:
            logger.error(
                f"Failed to generate chat completion: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "message_count": len(messages),
                    }
                },
            )
            raise

    async def generate_questions(
        self,
        context: str,
        count: int = 25,
        mode: str = "practice",
        topic: Optional[str] = None,
    ) -> str:
        """Generate questions from context using Together AI."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Together AI service not initialized")

        try:
            # Build prompt based on mode
            if mode == "quiz":
                prompt_template = """Based on the following context, generate {count} multiple-choice quiz questions.
Each question should have 4 options (A, B, C, D) with only one correct answer.
Format each question as:
Q: [Question]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [A/B/C/D]
Explanation: [Brief explanation]

Context:
{context}

{topic_instruction}

Generate the questions:"""
            else:  # practice mode
                prompt_template = """Based on the following context, generate {count} practice questions that help understand the key concepts.
Questions should be open-ended and encourage critical thinking.
Format each question as:
Q{{num}}: [Question]

Context:
{context}

{topic_instruction}

Generate the questions:"""

            topic_instruction = (
                f"Focus on the topic: {topic}" if topic else "Cover all key concepts from the context."
            )

            prompt = prompt_template.format(
                count=count,
                context=context[:4000],  # Limit context length
                topic_instruction=topic_instruction,
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert educational content creator. Generate high-quality questions that test understanding and promote learning.",
                },
                {"role": "user", "content": prompt},
            ]

            logger.info(
                "Generating questions",
                extra={
                    "extra_fields": {
                        "count": count,
                        "mode": mode,
                        "topic": topic,
                        "context_length": len(context),
                    }
                },
            )

            response = await self.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=4000,
            )

            logger.info(
                "Generated questions successfully",
                extra={
                    "extra_fields": {
                        "response_length": len(response),
                        "mode": mode,
                    }
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to generate questions: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "mode": mode,
                        "count": count,
                    }
                },
            )
            raise


# Global singleton instance
together_service = TogetherService()
