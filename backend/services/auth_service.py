"""
Authentication Service for Lumina IQ Backend.

Provides simple authentication functionality for the application.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("auth_service")


class AuthService:
    """Service for handling authentication."""

    def __init__(self):
        self.is_initialized = False
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def initialize(self) -> None:
        """Initialize authentication service."""
        try:
            logger.info("Initializing authentication service")
            self.is_initialized = True
            logger.info("Authentication service initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize authentication service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            raise

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            Dictionary containing authentication result
        """
        try:
            logger.info(
                "Login attempt",
                extra={"extra_fields": {"username": username}},
            )

            # Simple authentication against configured credentials
            if (
                username == settings.LOGIN_USERNAME
                and password == settings.LOGIN_PASSWORD
            ):
                # Generate session token
                session_token = self._generate_session_token(username)

                # Store session
                self.sessions[session_token] = {
                    "username": username,
                    "created_at": datetime.now().isoformat(),
                    "expires_at": (
                        datetime.now() + timedelta(hours=settings.SESSION_EXPIRE_HOURS)
                    ).isoformat(),
                }

                logger.info(
                    "Login successful",
                    extra={"extra_fields": {"username": username}},
                )

                return {
                    "access_token": session_token,
                    "token_type": "bearer",
                    "message": "Login successful",
                }
            else:
                logger.warning(
                    "Login failed - invalid credentials",
                    extra={"extra_fields": {"username": username}},
                )

                return {
                    "access_token": "",
                    "token_type": "bearer",
                    "message": "Invalid username or password",
                }

        except Exception as e:
            logger.error(
                f"Login error: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "username": username,
                    }
                },
            )
            return {
                "access_token": "",
                "token_type": "bearer",
                "message": "An error occurred during login",
            }

    async def logout(self, session_token: str) -> Dict[str, Any]:
        """
        Logout user by invalidating session token.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            Dictionary containing logout result
        """
        try:
            if session_token in self.sessions:
                username = self.sessions[session_token]["username"]
                del self.sessions[session_token]

                logger.info(
                    "Logout successful",
                    extra={"extra_fields": {"username": username}},
                )

                return {
                    "success": True,
                    "message": "Logout successful",
                }
            else:
                logger.warning("Logout attempt with invalid token")
                return {
                    "success": False,
                    "message": "Invalid session token",
                }

        except Exception as e:
            logger.error(
                f"Logout error: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            return {
                "success": False,
                "message": "An error occurred during logout",
            }

    async def verify_session(self, session_token: str) -> Dict[str, Any]:
        """
        Verify if session token is valid and not expired.
        
        Args:
            session_token: Session token to verify
            
        Returns:
            Dictionary containing verification result
        """
        try:
            if session_token not in self.sessions:
                return {
                    "valid": False,
                    "message": "Invalid session token",
                }

            session = self.sessions[session_token]
            expires_at = datetime.fromisoformat(session["expires_at"])

            if datetime.now() > expires_at:
                # Session expired, remove it
                del self.sessions[session_token]
                logger.info(
                    "Session expired",
                    extra={"extra_fields": {"username": session["username"]}},
                )
                return {
                    "valid": False,
                    "message": "Session expired",
                }

            return {
                "valid": True,
                "username": session["username"],
                "expires_at": session["expires_at"],
            }

        except Exception as e:
            logger.error(
                f"Session verification error: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            return {
                "valid": False,
                "message": "Error verifying session",
            }

    def _generate_session_token(self, username: str) -> str:
        """
        Generate a session token for the user.
        
        Args:
            username: Username for the session
            
        Returns:
            Session token string
        """
        import hashlib
        import secrets

        # Generate random token
        random_string = secrets.token_hex(32)
        timestamp = datetime.now().isoformat()

        # Create hash combining username, timestamp, and random string
        token_string = f"{username}:{timestamp}:{random_string}"
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()

        return token_hash

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            expired_tokens = []
            now = datetime.now()

            for token, session in self.sessions.items():
                expires_at = datetime.fromisoformat(session["expires_at"])
                if now > expires_at:
                    expired_tokens.append(token)

            for token in expired_tokens:
                del self.sessions[token]

            if expired_tokens:
                logger.info(
                    f"Cleaned up {len(expired_tokens)} expired sessions",
                    extra={"extra_fields": {"count": len(expired_tokens)}},
                )

            return len(expired_tokens)

        except Exception as e:
            logger.error(
                f"Session cleanup error: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            return 0

    def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        # Clean up expired sessions first
        self.cleanup_expired_sessions()
        return len(self.sessions)


# Global singleton instance
auth_service = AuthService()
