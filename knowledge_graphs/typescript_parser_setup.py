"""
TypeScript Parser Setup and Management

Handles Node.js dependencies and service lifecycle for the TypeScript parser.
Provides automatic installation and management for Python users.
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
import json
import platform

logger = logging.getLogger(__name__)


class TypeScriptParserSetup:
    """Manages Node.js dependencies and TypeScript parser service setup"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.node_modules_path = self.base_dir / "node_modules"
        self.package_json_path = self.base_dir / "package.json"
        self.parser_service_path = self.base_dir / "typescript_parser_service.js"
        self.is_docker = self._detect_docker()
        
    def _detect_docker(self) -> bool:
        """Detect if running inside Docker container"""
        return (
            os.path.exists('/.dockerenv') or 
            os.environ.get('DOCKER_CONTAINER', False) or
            (Path('/proc/1/cgroup').exists() and 
             'docker' in Path('/proc/1/cgroup').read_text())
        )
        
    def check_node_installed(self) -> bool:
        """Check if Node.js is installed"""
        try:
            result = subprocess.run(
                ["node", "--version"], 
                capture_output=True, 
                text=True,
                check=False
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"Node.js {version} is installed")
                # Check if version is 14+
                major_version = int(version.split('.')[0].replace('v', ''))
                if major_version < 14:
                    logger.warning(f"Node.js version {version} is too old. Version 14+ required.")
                    return False
                return True
        except (subprocess.SubprocessError, ValueError):
            pass
        return False
        
    def check_dependencies_installed(self) -> bool:
        """Check if npm dependencies are installed"""
        if not self.node_modules_path.exists():
            return False
            
        # Check if key dependencies exist
        required_deps = ["express", "typescript"]
        for dep in required_deps:
            if not (self.node_modules_path / dep).exists():
                return False
                
        return True
        
    def install_dependencies(self, force: bool = False) -> bool:
        """Install npm dependencies"""
        if not force and self.check_dependencies_installed():
            logger.info("Dependencies already installed")
            return True
            
        if not self.check_node_installed():
            logger.error("Node.js is not installed. Please install Node.js 14+ first.")
            logger.info("Visit https://nodejs.org/ to download and install Node.js")
            return False
            
        logger.info("Installing npm dependencies...")
        
        try:
            # Try to clean npm cache if there are issues
            if force:
                subprocess.run(
                    ["npm", "cache", "clean", "--force"],
                    cwd=self.base_dir,
                    capture_output=True
                )
            
            # Install dependencies
            # First try with force to handle cache issues
            result = subprocess.run(
                ["npm", "install", "--force"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                # Try cleaning cache and reinstalling
                logger.warning("npm install failed, cleaning cache and retrying...")
                subprocess.run(
                    ["npm", "cache", "clean", "--force"],
                    cwd=self.base_dir,
                    capture_output=True
                )
                
                result = subprocess.run(
                    ["npm", "install", "--force", "--registry", "https://registry.npmjs.org/"],
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
            if result.returncode == 0:
                logger.info("Dependencies installed successfully")
                return True
            else:
                logger.error(f"Failed to install dependencies: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False
            
    def ensure_package_json(self):
        """Ensure package.json exists with correct dependencies"""
        package_json = {
            "name": "typescript-parser-service",
            "version": "1.0.0",
            "description": "TypeScript/JavaScript parser service for Neo4j knowledge graph",
            "main": "typescript_parser_service.js",
            "scripts": {
                "start": "node typescript_parser_service.js",
                "test": "node test_parser.js"
            },
            "dependencies": {
                "express": "^4.18.2",
                "typescript": "^5.3.3"
            },
            "engines": {
                "node": ">=14.0.0"
            },
            "author": "",
            "license": "MIT"
        }
        
        # Check if package.json exists and has correct structure
        if self.package_json_path.exists():
            try:
                with open(self.package_json_path, 'r') as f:
                    existing = json.load(f)
                # Update dependencies if needed
                if existing.get('dependencies') != package_json['dependencies']:
                    existing['dependencies'] = package_json['dependencies']
                    with open(self.package_json_path, 'w') as f:
                        json.dump(existing, f, indent=2)
                    logger.info("Updated package.json dependencies")
            except:
                # If corrupted, recreate
                with open(self.package_json_path, 'w') as f:
                    json.dump(package_json, f, indent=2)
        else:
            # Create new package.json
            with open(self.package_json_path, 'w') as f:
                json.dump(package_json, f, indent=2)
            logger.info("Created package.json")
            
    def setup(self, force: bool = False) -> bool:
        """
        Complete setup for TypeScript parser
        
        Args:
            force: Force reinstall of dependencies
            
        Returns:
            True if setup successful
        """
        logger.info("Setting up TypeScript parser...")
        
        # Ensure package.json exists
        self.ensure_package_json()
        
        # Check if parser service exists
        if not self.parser_service_path.exists():
            logger.error(f"TypeScript parser service not found at {self.parser_service_path}")
            return False
            
        # Install dependencies
        if not self.install_dependencies(force):
            return False
            
        logger.info("TypeScript parser setup complete!")
        return True
        
    def get_install_instructions(self) -> str:
        """Get platform-specific installation instructions"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return """
To install Node.js on macOS:
1. Using Homebrew: brew install node
2. Or download from: https://nodejs.org/

After installation, run this script again.
"""
        elif system == "Linux":
            return """
To install Node.js on Linux:
1. Ubuntu/Debian: sudo apt-get update && sudo apt-get install nodejs npm
2. RHEL/CentOS: sudo yum install nodejs npm
3. Or use NodeSource: https://github.com/nodesource/distributions

After installation, run this script again.
"""
        elif system == "Windows":
            return """
To install Node.js on Windows:
1. Download installer from: https://nodejs.org/
2. Or using Chocolatey: choco install nodejs

After installation, run this script again.
"""
        else:
            return "Please install Node.js 14+ from https://nodejs.org/"


def setup_typescript_parser(force: bool = False) -> bool:
    """
    Convenience function to setup TypeScript parser
    
    Args:
        force: Force reinstall of dependencies
        
    Returns:
        True if setup successful
    """
    setup = TypeScriptParserSetup()
    
    if not setup.check_node_installed():
        print("Node.js is not installed!")
        print(setup.get_install_instructions())
        return False
        
    return setup.setup(force)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup TypeScript parser dependencies")
    parser.add_argument("--force", action="store_true", help="Force reinstall dependencies")
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = setup_typescript_parser(args.force)
    sys.exit(0 if success else 1)