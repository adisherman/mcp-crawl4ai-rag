"""
Module Resolution System for TypeScript/JavaScript

Implements a robust module resolution algorithm following Node.js module resolution
with TypeScript extensions, supporting:
- Relative imports
- Absolute imports
- Node modules
- TypeScript path mappings
- Index files
- File extensions
- Barrel exports
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResolvedModule:
    """Represents a resolved module"""
    module_path: str  # The normalized module path (e.g., "src.components.Button")
    file_path: Path   # The actual file path
    is_external: bool = False
    is_barrel: bool = False
    exports: List[str] = None
    
    def __post_init__(self):
        if self.exports is None:
            self.exports = []


class ModuleResolver:
    """Resolves module imports following Node.js and TypeScript conventions"""
    
    def __init__(self, project_root: Path, config: Optional[Dict] = None):
        self.project_root = project_root
        self.config = config or {}
        
        # Load TypeScript config if available
        self.ts_config = self._load_tsconfig()
        
        # Override with config if provided
        if config and 'ts_config' in config:
            self.ts_config = config['ts_config']
        
        # Default file extensions to try
        self.extensions = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.json']
        
        # Default index file names
        self.index_names = ['index']
        
        # Common source directories
        self.source_dirs = ['src', 'lib', 'app', 'source', 'packages']
        
        # Cache for resolved modules
        self._resolution_cache: Dict[Tuple[str, str], Optional[ResolvedModule]] = {}
        
        # Allow resolution without file existence check (for validation scenarios)
        self.require_file_exists = config.get('require_file_exists', True)
    
    def _get_path_aliases(self) -> List[str]:
        """Get all configured path aliases"""
        if not self.ts_config:
            return []
        
        compiler_options = self.ts_config.get('compilerOptions', {})
        paths = compiler_options.get('paths', {})
        return list(paths.keys())
    
    def _is_path_alias(self, import_path: str) -> bool:
        """Check if import path matches any configured alias"""
        if not self.ts_config:
            return False
        
        compiler_options = self.ts_config.get('compilerOptions', {})
        paths = compiler_options.get('paths', {})
        
        for alias in paths.keys():
            # Handle exact matches and wildcard patterns
            if '*' in alias:
                # Convert to simple pattern matching
                prefix = alias.replace('*', '')
                if import_path.startswith(prefix):
                    return True
            elif import_path == alias or import_path.startswith(alias + '/'):
                return True
        
        return False
    
    def _load_tsconfig(self) -> Optional[Dict]:
        """Load TypeScript configuration"""
        tsconfig_path = self.project_root / 'tsconfig.json'
        if not tsconfig_path.exists():
            return None
            
        try:
            with open(tsconfig_path, 'r') as f:
                content = f.read()
                
            # Remove comments (simple approach)
            lines = []
            for line in content.split('\n'):
                comment_idx = line.find('//')
                if comment_idx >= 0:
                    line = line[:comment_idx]
                lines.append(line)
            content = '\n'.join(lines)
            
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to load tsconfig.json: {e}")
            return None
    
    def resolve(self, import_path: str, from_file: Path) -> Optional[ResolvedModule]:
        """
        Resolve a module import path
        
        Args:
            import_path: The import path (e.g., './component', 'react', '@/utils')
            from_file: The file that contains the import
            
        Returns:
            ResolvedModule or None if not found
        """
        # Check cache
        cache_key = (import_path, str(from_file))
        if cache_key in self._resolution_cache:
            return self._resolution_cache[cache_key]
        
        result = None
        
        # Determine import type
        if import_path.startswith('.'):
            # Relative import
            result = self._resolve_relative(import_path, from_file)
        elif self._is_path_alias(import_path):
            # Check if it matches any configured path alias
            result = self._resolve_alias(import_path, from_file)
        elif import_path.startswith('@/'):
            # This is an internal alias pattern
            result = self._resolve_alias(import_path, from_file)
            if not result:
                # Even if not resolved, mark as internal
                result = ResolvedModule(
                    module_path=import_path,
                    file_path=Path(import_path),
                    is_external=False
                )
        elif import_path.startswith('@') and '/' in import_path:
            # Could be a scoped package or an alias - check aliases first
            result = self._resolve_alias(import_path, from_file) or self._resolve_external(import_path)
        elif import_path.startswith('@'):
            # Likely a scoped package without sub-paths
            result = self._resolve_external(import_path)
        elif '/' not in import_path or import_path.split('/')[0] in ['node_modules']:
            # Likely an external package
            result = self._resolve_external(import_path)
        else:
            # Try absolute import first, then external
            result = self._resolve_absolute(import_path) or self._resolve_external(import_path)
        
        # Cache the result
        self._resolution_cache[cache_key] = result
        return result
    
    def _resolve_relative(self, import_path: str, from_file: Path) -> Optional[ResolvedModule]:
        """Resolve relative imports like './component' or '../utils/helper'"""
        # Get the directory of the importing file
        from_dir = from_file.parent
        
        # Resolve the relative path
        if import_path.startswith('./'):
            target_path = from_dir / import_path[2:]
        elif import_path.startswith('../'):
            # Count levels up
            levels_up = 0
            remaining = import_path
            while remaining.startswith('../'):
                levels_up += 1
                remaining = remaining[3:]
            
            # Go up the required levels
            target_dir = from_dir
            for _ in range(levels_up):
                target_dir = target_dir.parent
                # Stop at project root to avoid going outside
                if target_dir == self.project_root:
                    break
            
            target_path = target_dir / remaining
        else:
            # Should not happen for relative imports
            return None
        
        # Try to resolve the file
        resolved_file = self._try_resolve_file(target_path)
        if resolved_file:
            return self._create_resolved_module(resolved_file, from_file)
        
        return None
    
    def _resolve_absolute(self, import_path: str) -> Optional[ResolvedModule]:
        """Resolve absolute imports like 'components/Button'"""
        # Try from project root
        target_path = self.project_root / import_path
        resolved_file = self._try_resolve_file(target_path)
        if resolved_file:
            return self._create_resolved_module(resolved_file, self.project_root)
        
        # Try from common source directories
        for src_dir in self.source_dirs:
            target_path = self.project_root / src_dir / import_path
            resolved_file = self._try_resolve_file(target_path)
            if resolved_file:
                return self._create_resolved_module(resolved_file, self.project_root / src_dir)
        
        return None
    
    def _resolve_alias(self, import_path: str, from_file: Path) -> Optional[ResolvedModule]:
        """Resolve alias imports using TypeScript path mappings"""
        if not self.ts_config:
            return None
        
        compiler_options = self.ts_config.get('compilerOptions', {})
        paths = compiler_options.get('paths', {})
        base_url = compiler_options.get('baseUrl', '.')
        base_path = self.project_root / base_url
        
        # Try each path mapping
        for alias, mappings in paths.items():
            # Convert glob pattern to regex
            if '*' in alias:
                # Simple glob matching (e.g., '@/*' matches '@/anything')
                pattern = alias.replace('*', '(.*)')
                import re
                match = re.match(f"^{pattern}$", import_path)
                if match:
                    captured = match.group(1) if match.groups() else ''
                    
                    # Try each mapping
                    for mapping in mappings:
                        if '*' in mapping:
                            resolved_path = mapping.replace('*', captured)
                        else:
                            resolved_path = mapping
                        
                        target_path = base_path / resolved_path
                        resolved_file = self._try_resolve_file(target_path)
                        if resolved_file:
                            return self._create_resolved_module(resolved_file, base_path)
            else:
                # Exact match
                if import_path == alias:
                    for mapping in mappings:
                        target_path = base_path / mapping
                        resolved_file = self._try_resolve_file(target_path)
                        if resolved_file:
                            return self._create_resolved_module(resolved_file, base_path)
        
        return None
    
    def _resolve_external(self, import_path: str) -> Optional[ResolvedModule]:
        """Resolve external package imports"""
        # For external packages, we don't resolve to actual files
        # Just mark them as external
        return ResolvedModule(
            module_path=import_path,
            file_path=Path(import_path),  # Placeholder path
            is_external=True
        )
    
    def _try_resolve_file(self, base_path: Path) -> Optional[Path]:
        """Try to resolve a file path with different extensions and index files"""
        # Clean the path of any existing extension
        if base_path.suffix in self.extensions:
            base_path = base_path.with_suffix('')
        
        # If we don't require file existence, just return the most likely path
        if not self.require_file_exists:
            # Try with common extensions
            for ext in self.extensions:
                file_path = base_path.with_suffix(ext)
                # Return the first TypeScript/JavaScript extension
                if ext in ['.ts', '.tsx', '.js', '.jsx']:
                    return file_path
            # Default to .ts if no match
            return base_path.with_suffix('.ts')
        
        # Original logic for when files must exist
        # Try exact file with each extension
        for ext in self.extensions:
            file_path = base_path.with_suffix(ext)
            if file_path.exists() and file_path.is_file():
                return file_path
        
        # Try as directory with index files
        if base_path.exists() and base_path.is_dir():
            for index_name in self.index_names:
                for ext in self.extensions:
                    index_path = base_path / f"{index_name}{ext}"
                    if index_path.exists() and index_path.is_file():
                        return index_path
        
        # Try without extension (for cases like 'require("./file")')
        if base_path.exists() and base_path.is_file():
            return base_path
        
        return None
    
    def _create_resolved_module(self, file_path: Path, base_path: Path) -> ResolvedModule:
        """Create a ResolvedModule from a file path"""
        # Always calculate relative path from project root for consistent Neo4j paths
        try:
            relative_path = file_path.relative_to(self.project_root)
        except ValueError:
            # If file is outside project root, use full path
            relative_path = file_path
        
        # Convert to module path (forward slashes to match Neo4j format)
        parts = list(relative_path.parts)
        
        # Remove extension from last part
        if parts and '.' in parts[-1]:
            name, ext = os.path.splitext(parts[-1])
            if ext in self.extensions:
                parts[-1] = name
        
        # Use forward slashes to match Neo4j storage format
        module_path = '/'.join(parts)
        
        # Check if it's a barrel export (index file)
        is_barrel = file_path.stem in self.index_names
        
        return ResolvedModule(
            module_path=module_path,
            file_path=file_path,
            is_barrel=is_barrel
        )
    
    def normalize_import_path(self, import_path: str, from_file: Path) -> str:
        """
        Normalize an import path to a consistent module format
        
        Args:
            import_path: The import path to normalize
            from_file: The file containing the import
            
        Returns:
            Normalized module path (e.g., "src/components/Button")
        """
        resolved = self.resolve(import_path, from_file)
        if resolved and not resolved.is_external:
            return resolved.module_path
        return import_path
    
    def get_module_exports(self, module_path: str) -> List[str]:
        """
        Get the exports from a module (requires parsing)
        
        This is a placeholder - actual implementation would parse the file
        """
        # This would need to integrate with the TypeScript parser
        # For now, return empty list
        return []
    
    def is_node_module(self, import_path: str) -> bool:
        """Check if an import is from node_modules"""
        # Simple heuristic: no relative path and not in source
        if import_path.startswith('.'):
            return False
        
        # Check if it could be resolved as absolute
        if self._resolve_absolute(import_path):
            return False
        
        # Otherwise, likely a node module
        return True
    
    def find_all_imports(self, file_path: Path) -> List[Tuple[str, ResolvedModule]]:
        """
        Find all imports in a file and resolve them
        
        This is a placeholder - actual implementation would parse the file
        """
        # This would need to integrate with the TypeScript parser
        return []
    
    def debug_resolution(self, import_path: str, from_file: Path) -> Dict[str, any]:
        """
        Debug helper to show the resolution process
        
        Args:
            import_path: The import path to resolve
            from_file: The file containing the import
            
        Returns:
            Dictionary with resolution details
        """
        from_file = Path(from_file) if not isinstance(from_file, Path) else from_file
        resolved = self.resolve(import_path, from_file)
        
        result = {
            'import_path': import_path,
            'from_file': str(from_file),
            'from_dir': str(from_file.parent),
            'resolved': resolved is not None,
        }
        
        if resolved:
            result.update({
                'module_path': resolved.module_path,
                'file_path': str(resolved.file_path),
                'is_external': resolved.is_external,
                'is_barrel': resolved.is_barrel,
            })
        
        return result


def create_platform_safe_path(path_str: str) -> Path:
    """Create a platform-safe Path object from a string"""
    # Handle different path separators
    if '\\' in path_str and '/' in path_str:
        # Mixed separators, normalize to current platform
        path_str = path_str.replace('\\', os.sep).replace('/', os.sep)
    elif '\\' in path_str:
        # Windows-style path
        path_str = path_str.replace('\\', os.sep)
    elif '/' in path_str:
        # Unix-style path
        path_str = path_str.replace('/', os.sep)
    
    return Path(path_str)


def get_relative_module_path(file_path: Path, project_root: Path, source_dirs: List[str] = None) -> str:
    """
    Get a module path relative to the project structure
    
    Args:
        file_path: The file path to convert
        project_root: The project root directory
        source_dirs: List of source directories to check
        
    Returns:
        Module path string (e.g., "src/components/Button")
    """
    if source_dirs is None:
        source_dirs = ['src', 'lib', 'app', 'source']
    
    try:
        # Try relative to project root
        relative = file_path.relative_to(project_root)
        
        # Check if it's in a source directory
        parts = relative.parts
        if parts and parts[0] in source_dirs:
            # Keep the source directory
            module_parts = list(parts)
        else:
            # Prepend 'src' if not in a known source directory
            module_parts = ['src'] + list(parts)
        
        # Remove file extension
        if module_parts:
            name, ext = os.path.splitext(module_parts[-1])
            if ext in ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs']:
                module_parts[-1] = name
        
        # Use forward slashes to match Neo4j storage format
        return '/'.join(module_parts)
    except ValueError:
        # File is outside project root
        return file_path.stem