#!/usr/bin/env python3
"""
Deployment script for Learning App backend.
Supports environment-specific deployments with Docker and traditional server setups.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests


class Deployer:
    """Deployment manager for Learning App backend."""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.backend_dir = Path(__file__).parent

        # Environment-specific settings
        self.env_configs = {
            "development": {
                "docker_compose_file": "docker-compose.yml",
                "profile": None,
                "health_url": "http://localhost:8000/health"
            },
            "staging": {
                "docker_compose_file": "docker-compose.staging.yml",
                "profile": None,
                "health_url": "http://localhost:8000/health"
            },
            "production": {
                "docker_compose_file": "docker-compose.yml",
                "profile": None,
                "health_url": "http://localhost:8000/health"
            }
        }

    def run_command(self, command: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command with proper error handling."""
        try:
            print(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                check=check,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(command)}")
            print(f"Error: {e.stderr}")
            if check:
                sys.exit(1)
            return e

    def check_docker_availability(self) -> bool:
        """Check if Docker and Docker Compose are available."""
        try:
            self.run_command(["docker", "--version"])
            self.run_command(["docker", "compose", "version"])
            return True
        except subprocess.CalledProcessError:
            return False

    def wait_for_health_check(self, url: str, timeout: int = 300) -> bool:
        """Wait for service health check to pass."""
        print(f"Waiting for health check at {url}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print("Health check passed!")
                    return True
            except requests.RequestException:
                pass

            print("Health check failed, retrying...")
            time.sleep(10)

        print(f"Health check timeout after {timeout} seconds")
        return False

    def deploy_with_docker(self) -> bool:
        """Deploy using Docker Compose."""
        print(f"🚀 Deploying with Docker Compose ({self.environment} environment)")

        # Build and start services
        compose_file = self.env_configs[self.environment]["docker_compose_file"]

        # Build images
        self.run_command(["docker", "compose", "-f", compose_file, "build"])

        # Start services
        self.run_command(["docker", "compose", "-f", compose_file, "up", "-d"])

        # Wait for health checks
        health_url = self.env_configs[self.environment]["health_url"]
        if self.wait_for_health_check(health_url):
            print("✅ Deployment successful!")
            return True
        else:
            print("❌ Deployment failed - health check timeout")
            return False

    def deploy_traditional(self) -> bool:
        """Deploy using traditional server setup (systemd/gunicorn)."""
        print(f"🚀 Deploying with traditional setup ({self.environment} environment)")

        # Check if virtual environment exists
        venv_path = self.backend_dir / ".venv"
        if not venv_path.exists():
            print("Creating virtual environment...")
            self.run_command(["python3", "-m", "venv", str(venv_path)], cwd=self.backend_dir)

        # Activate virtual environment and install dependencies
        pip_path = venv_path / "bin" / "pip"
        self.run_command([str(pip_path), "install", "-r", "requirements.txt"], cwd=self.backend_dir)

        # Create necessary directories
        log_dir = Path("/var/log/learning-app")
        run_dir = Path("/var/run/learning-app")
        cache_dir = self.backend_dir / "cache"

        for directory in [log_dir, run_dir, cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            # Set proper permissions (would need sudo in production)
            os.chmod(directory, 0o755)

        # Start service with gunicorn
        gunicorn_cmd = [
            str(venv_path / "bin" / "gunicorn"),
            "--config", "gunicorn.conf.py",
            "main:app"
        ]

        print("Starting Gunicorn server...")
        # In production, this should be managed by systemd
        self.run_command(gunicorn_cmd, cwd=self.backend_dir, check=False)

        # Wait for health check
        if self.wait_for_health_check("http://localhost:8000/health"):
            print("✅ Deployment successful!")
            return True
        else:
            print("❌ Deployment failed - health check timeout")
            return False

    def stop_services(self) -> bool:
        """Stop running services."""
        print("🛑 Stopping services...")

        if self.check_docker_availability():
            compose_file = self.env_configs[self.environment]["docker_compose_file"]
            self.run_command(["docker", "compose", "-f", compose_file, "down"])
            return True
        else:
            # For traditional deployment, kill gunicorn processes
            self.run_command(["pkill", "-f", "gunicorn"], check=False)
            return True

    def restart_services(self) -> bool:
        """Restart running services."""
        print("🔄 Restarting services...")

        if not self.stop_services():
            return False

        time.sleep(5)  # Wait for clean shutdown

        if self.check_docker_availability():
            return self.deploy_with_docker()
        else:
            return self.deploy_traditional()

    def show_status(self) -> None:
        """Show deployment status."""
        print(f"📊 Deployment Status ({self.environment})")

        if self.check_docker_availability():
            compose_file = self.env_configs[self.environment]["docker_compose_file"]
            result = self.run_command(["docker", "compose", "-f", compose_file, "ps"], check=False)
            print(result.stdout)
        else:
            # Check for running gunicorn processes
            result = self.run_command(["pgrep", "-f", "gunicorn"], check=False)
            if result.returncode == 0:
                print("Gunicorn processes running:")
                print(result.stdout)
            else:
                print("No gunicorn processes found")

    def show_logs(self, service: Optional[str] = None, follow: bool = False) -> None:
        """Show service logs."""
        if self.check_docker_availability():
            compose_file = self.env_configs[self.environment]["docker_compose_file"]
            cmd = ["docker", "compose", "-f", compose_file, "logs"]
            if service:
                cmd.extend(["-f", service])
            if follow:
                cmd.append("-f")
            self.run_command(cmd, check=False)
        else:
            print("Log viewing not implemented for traditional deployment")

    def deploy(self) -> bool:
        """Main deployment method."""
        if self.check_docker_availability():
            return self.deploy_with_docker()
        else:
            print("Docker not available, falling back to traditional deployment")
            return self.deploy_traditional()


def main():
    parser = argparse.ArgumentParser(description="Deploy Learning App backend")
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        default="production",
        help="Deployment environment"
    )
    parser.add_argument(
        "action",
        choices=["deploy", "stop", "restart", "status", "logs"],
        help="Action to perform"
    )
    parser.add_argument(
        "--service",
        help="Service name for logs (docker only)"
    )
    parser.add_argument(
        "--follow", "-f",
        action="store_true",
        help="Follow logs"
    )

    args = parser.parse_args()

    deployer = Deployer(args.environment)

    if args.action == "deploy":
        success = deployer.deploy()
    elif args.action == "stop":
        success = deployer.stop_services()
    elif args.action == "restart":
        success = deployer.restart_services()
    elif args.action == "status":
        deployer.show_status()
        success = True
    elif args.action == "logs":
        deployer.show_logs(args.service, args.follow)
        success = True
    else:
        print(f"Unknown action: {args.action}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()