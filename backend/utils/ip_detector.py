#!/usr/bin/env python3
"""
IP Detection and Frontend Environment Update Utility

This module provides functionality to automatically detect the local IP address
and update the frontend .env file with the correct backend API URL.
"""

import socket
import os
import re
from pathlib import Path
from utils.logger import get_logger

# Use enhanced logger
logger = get_logger("ip_detector")


def get_local_ip():
    """
    Get the local IP address of the machine.

    Returns:
        str: The local IP address, or '127.0.0.1' if detection fails
    """
    try:
        # Create a socket connection to determine the local IP
        # This method works by connecting to a remote address (doesn't actually send data)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to Google's DNS server (8.8.8.8) on port 80
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            logger.info(f"Local IP address detected: {local_ip}")
            return local_ip
    except Exception as e:
        logger.warning(
            f"Could not detect local IP address: {str(e)}",
        )
        logger.info("Falling back to localhost (127.0.0.1)")
        return "127.0.0.1"


def update_frontend_env(ip_address, port=8000):
    """
    Update the frontend .env file with the detected IP address.

    Args:
        ip_address (str): The IP address to use
        port (int): The port number (default: 8000)
    """
    try:
        # Get the path to the frontend .env file
        backend_dir = Path(__file__).parent.parent
        frontend_env_path = backend_dir.parent / "frontend" / ".env"

        # Create the new API URL
        new_api_url = f"http://{ip_address}:{port}/api"

        # Read the current .env file content
        if frontend_env_path.exists():
            with open(frontend_env_path, "r") as f:
                content = f.read()
        else:
            content = ""

        # Update or add the NEXT_PUBLIC_API_BASE_URL line
        api_url_pattern = r"^NEXT_PUBLIC_API_BASE_URL=.*$"
        new_line = f"NEXT_PUBLIC_API_BASE_URL={new_api_url}"

        if re.search(api_url_pattern, content, re.MULTILINE):
            # Replace existing line
            updated_content = re.sub(
                api_url_pattern, new_line, content, flags=re.MULTILINE
            )
        else:
            # Add new line
            if content and not content.endswith("\n"):
                content += "\n"
            updated_content = content + f"# Backend API Configuration\n{new_line}\n"

        # Write the updated content back to the file
        frontend_env_path.parent.mkdir(parents=True, exist_ok=True)
        with open(frontend_env_path, "w") as f:
            f.write(updated_content)

        logger.info(f"Updated frontend .env file with new API URL: {new_api_url}")
        logger.info(f"Updated frontend .env file: {str(frontend_env_path)}")

    except Exception as e:
        logger.error("Error updating frontend .env file", error=str(e))
        logger.info(
            "Please manually update the NEXT_PUBLIC_API_BASE_URL in frontend/.env"
        )
        logger.info(f"Set API URL: {f'http://{ip_address}:{port}/api'}")


def setup_frontend_env(port=8000):
    """
    Main function to detect IP and update frontend environment.

    Args:
        port (int): The port number the backend will run on (default: 8000)
    """
    print("🔍 Detecting local IP address...")
    ip_address = get_local_ip()
    print(f"📍 Detected IP: {ip_address}")

    print("🔄 Updating frontend .env file...")
    update_frontend_env(ip_address, port)

    return ip_address


if __name__ == "__main__":
    # For testing purposes
    detected_ip = setup_frontend_env()
    print(
        f"\n🎉 Setup complete! Backend will be accessible at: http://{detected_ip}:8000"
    )
