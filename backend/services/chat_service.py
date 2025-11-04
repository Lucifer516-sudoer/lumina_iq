"""
Chat Service for Lumina IQ RAG Backend.

Handles chat and question generation using LangChain with Together AI.
"""

from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("chat_service")


class ChatService:
    """Service for chat and question generation using LangChain + Together AI."""

    def __init__(self):
        self.llm: Optional[ChatOpenAI] = None
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize LangChain chat model with Together AI."""
        try:
            if not settings.TOGETHER_API_KEY:
                logger.warning("TOGETHER_API_KEY not configured")
                return

            logger.info(
                "Initializing chat service",
                extra={
                    "extra_fields": {
                        "model": settings.TOGETHER_MODEL,
                        "provider": "Together AI (via LangChain)",
                    }
                },
            )

            # Initialize LangChain ChatOpenAI with Together AI
            self.llm = ChatOpenAI(
                model=settings.TOGETHER_MODEL,
                openai_api_base=settings.TOGETHER_BASE_URL,
                openai_api_key=settings.TOGETHER_API_KEY,
                temperature=0.7,
                max_tokens=4000,
            )

            self.is_initialized = True
            logger.info("Chat service initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize chat service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            raise

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate chat response using LangChain."""
        if not self.is_initialized or not self.llm:
            raise RuntimeError("Chat service not initialized")

        try:
            logger.debug(
                "Generating chat response",
                extra={
                    "extra_fields": {
                        "message_count": len(messages),
                        "temperature": temperature,
                    }
                },
            )

            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    langchain_messages.append(AIMessage(content=content))

            # Update LLM parameters if needed
            if max_tokens:
                self.llm.max_tokens = max_tokens
            self.llm.temperature = temperature

            # Generate response
            response = await self.llm.ainvoke(langchain_messages)
            content = response.content

            logger.debug(
                "Generated chat response successfully",
                extra={
                    "extra_fields": {
                        "response_length": len(content),
                    }
                },
            )

            return content

        except Exception as e:
            logger.error(
                f"Failed to generate chat response: {str(e)}",
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
        """Generate questions from context."""
        if not self.is_initialized or not self.llm:
            raise RuntimeError("Chat service not initialized")

        try:
            logger.info(
                f"Generating questions from context: count={count}, mode={mode}, topic={topic}, context_length={len(context)}"
            )

            # Build prompt based on mode
            if mode == "quiz":
                system_prompt = """You are an expert educational content creator specializing in creating high-quality quiz questions.
Generate multiple-choice quiz questions that test understanding and critical thinking.
Each question should be clear, unambiguous, and have only one correct answer.

IMPORTANT: Return your response as a JSON object. Do NOT use markdown code blocks, bold, italic, or special formatting INSIDE the question text itself. Keep all question content as plain text."""

                user_prompt = """Based on the following context, generate {count} multiple-choice quiz questions.

Return your response as a valid JSON object in this EXACT format:
{{
  "questions": [
    "Q1: [Question text in plain text]\\nA) [Option A]\\nB) [Option B]\\nC) [Option C]\\nD) [Option D]\\nCorrect Answer: [A/B/C/D]\\nExplanation: [Brief explanation]",
    "Q2: [Question text in plain text]\\nA) [Option A]\\nB) [Option B]\\nC) [Option C]\\nD) [Option D]\\nCorrect Answer: [A/B/C/D]\\nExplanation: [Brief explanation]"
  ]
}}

Context:
{context}

{topic_instruction}

CRITICAL: Return ONLY the JSON object, no extra text before or after. Each question should be a single string with newline characters (\\n) separating lines. Do NOT use markdown formatting like backticks, asterisks, or code blocks inside the question text.

Generate the questions now:"""

            else:  # practice mode
                system_prompt = """You are an expert educational content creator specializing in creating thought-provoking practice questions.
Generate open-ended questions that encourage critical thinking and deep understanding.

IMPORTANT: Return your response as a JSON object with plain text questions."""

                user_prompt = """Based on the following context, generate {count} practice questions that help understand key concepts.

Return your response as a valid JSON object in this EXACT format:
{{
  "questions": [
    "Q1: [Question text]",
    "Q2: [Question text]",
    "Q3: [Question text]"
  ]
}}

Context:
{context}

{topic_instruction}

CRITICAL: Return ONLY the JSON object, no extra text. Do NOT use markdown formatting inside the questions.

Generate the questions now:"""

            topic_instruction = (
                f"Focus specifically on the topic: {topic}"
                if topic
                else "Cover all key concepts from the context comprehensively."
            )

            # Limit context to avoid token limits
            context_limited = context[:4000] if len(context) > 4000 else context

            # Format prompts
            formatted_user_prompt = user_prompt.format(
                count=count,
                context=context_limited,
                topic_instruction=topic_instruction,
            )

            # Generate response
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_user_prompt},
            ]

            response = await self.generate_response(
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
                        "count": count,
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

    async def generate_chat_response(
        self, query: str, context: str
    ) -> str:
        """Generate a conversational chat response using RAG context."""
        if not self.is_initialized or not self.llm:
            raise RuntimeError("Chat service not initialized")

        try:
            logger.info(f"Generating chat response - query_length: {len(query)}, context_length: {len(context)}")

            system_prompt = """You are a helpful AI assistant with expertise in the documents provided. 
Your role is to answer questions conversationally and naturally based on the context given.
Be concise, accurate, and helpful. If the context doesn't contain enough information to fully answer the question, say so."""

            user_prompt = f"""Context from documents:
{context[:4000]}

User question: {query}

Please provide a clear, conversational answer based on the context above:"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.generate_response(
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )

            logger.info(f"Generated chat response successfully - response_length: {len(response)}")

            return response

        except Exception as e:
            logger.error(f"Failed to generate chat response: {str(e)}")
            raise

    async def summarize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Summarize text using LangChain."""
        if not self.is_initialized or not self.llm:
            raise RuntimeError("Chat service not initialized")

        try:
            logger.debug(
                "Summarizing text",
                extra={"extra_fields": {"text_length": len(text)}},
            )

            system_prompt = "You are a helpful assistant that creates concise and accurate summaries."
            user_prompt = f"Summarize the following text:\n\n{text}"

            if max_length:
                user_prompt += (
                    f"\n\nLimit the summary to approximately {max_length} words."
                )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            summary = await self.generate_response(messages=messages, temperature=0.5)

            logger.debug(
                "Generated summary successfully",
                extra={
                    "extra_fields": {
                        "original_length": len(text),
                        "summary_length": len(summary),
                    }
                },
            )

            return summary

        except Exception as e:
            logger.error(
                f"Failed to summarize text: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "text_length": len(text),
                    }
                },
            )
            raise


# Global singleton instance
chat_service = ChatService()
