"""
Framework Detector for TypeScript/JavaScript Projects

Detects which frontend framework(s) are being used in a project by analyzing:
- Package.json dependencies
- Configuration files
- Import patterns
- File patterns
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Framework(Enum):
    """Supported frontend frameworks"""
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    SOLID = "solid"
    PREACT = "preact"
    QWIK = "qwik"
    LIT = "lit"
    ALPINE = "alpine"
    VANILLA = "vanilla"  # Plain JS/TS with no framework


@dataclass
class FrameworkInfo:
    """Information about a detected framework"""
    framework: Framework
    version: Optional[str] = None
    confidence: float = 0.0
    indicators: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    entry_patterns: List[str] = field(default_factory=list)
    component_patterns: List[str] = field(default_factory=list)
    
    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.8


class FrameworkDetector:
    """Detects frontend frameworks used in a project"""
    
    def __init__(self):
        # Framework detection patterns
        self.framework_patterns = {
            Framework.REACT: {
                'dependencies': ['react', 'react-dom'],
                'dev_dependencies': ['@types/react', '@types/react-dom', 'react-scripts'],
                'config_files': ['next.config.js', 'gatsby-config.js', '.eslintrc.react.js'],
                'file_extensions': ['.jsx', '.tsx'],
                'import_patterns': [
                    r'from\s+[\'"]react[\'"]',
                    r'import\s+React',
                    r'require\([\'"]react[\'"]'
                ],
                'code_patterns': [
                    r'React\.Component',
                    r'React\.FC',
                    r'React\.createElement',
                    r'useState\s*\(',
                    r'useEffect\s*\(',
                    r'<[A-Z]\w+',  # JSX component
                ]
            },
            Framework.VUE: {
                'dependencies': ['vue', '@vue/core'],
                'dev_dependencies': ['@vue/cli', '@vue/compiler-sfc', 'vue-loader'],
                'config_files': ['vue.config.js', 'nuxt.config.js', 'vite.config.js'],
                'file_extensions': ['.vue'],
                'import_patterns': [
                    r'from\s+[\'"]vue[\'"]',
                    r'import\s+\{[^}]*createApp[^}]*\}\s+from\s+[\'"]vue[\'"]',
                    r'import\s+Vue\s+from'
                ],
                'code_patterns': [
                    r'<template>',
                    r'<script\s+setup>',
                    r'defineComponent\s*\(',
                    r'ref\s*\(',
                    r'reactive\s*\(',
                    r'computed\s*\(',
                    r'@click\s*=',
                    r'v-model\s*=',
                    r'v-if\s*=',
                    r'v-for\s*='
                ]
            },
            Framework.ANGULAR: {
                'dependencies': ['@angular/core', '@angular/common'],
                'dev_dependencies': ['@angular/cli', '@angular-devkit/build-angular'],
                'config_files': ['angular.json', '.angular-cli.json', 'angular.config.js'],
                'file_extensions': ['.component.ts', '.service.ts', '.module.ts'],
                'import_patterns': [
                    r'from\s+[\'"]@angular',
                    r'import\s+\{[^}]*Component[^}]*\}\s+from\s+[\'"]@angular/core[\'"]'
                ],
                'code_patterns': [
                    r'@Component\s*\(',
                    r'@Injectable\s*\(',
                    r'@NgModule\s*\(',
                    r'@Directive\s*\(',
                    r'@Pipe\s*\(',
                    r'\*ngFor\s*=',
                    r'\*ngIf\s*=',
                    r'\[(ngModel|formControl)\]\s*=',
                    r'\(click\)\s*='
                ]
            },
            Framework.SVELTE: {
                'dependencies': ['svelte'],
                'dev_dependencies': ['@sveltejs/kit', '@sveltejs/vite-plugin-svelte', 'svelte-loader'],
                'config_files': ['svelte.config.js', 'sveltekit.config.js'],
                'file_extensions': ['.svelte'],
                'import_patterns': [
                    r'from\s+[\'"]svelte',
                    r'import\s+\{[^}]*onMount[^}]*\}\s+from\s+[\'"]svelte[\'"]'
                ],
                'code_patterns': [
                    r'<script>',
                    r'\$:\s*\w+\s*=',  # Reactive declarations
                    r'on:click\s*=',
                    r'bind:\w+\s*=',
                    r'{#if\s+',
                    r'{#each\s+',
                    r'{@html\s+'
                ]
            },
            Framework.SOLID: {
                'dependencies': ['solid-js'],
                'dev_dependencies': ['vite-plugin-solid', 'solid-refresh'],
                'config_files': ['solid.config.js'],
                'file_extensions': ['.jsx', '.tsx'],
                'import_patterns': [
                    r'from\s+[\'"]solid-js[\'"]',
                    r'import\s+\{[^}]*createSignal[^}]*\}\s+from\s+[\'"]solid-js[\'"]'
                ],
                'code_patterns': [
                    r'createSignal\s*\(',
                    r'createEffect\s*\(',
                    r'createMemo\s*\(',
                    r'<Show\s+',
                    r'<For\s+'
                ]
            },
            Framework.PREACT: {
                'dependencies': ['preact'],
                'dev_dependencies': ['@preact/preset-vite', 'preact-render-to-string'],
                'config_files': ['preact.config.js'],
                'file_extensions': ['.jsx', '.tsx'],
                'import_patterns': [
                    r'from\s+[\'"]preact[\'"]',
                    r'import\s+\{[^}]*h[^}]*\}\s+from\s+[\'"]preact[\'"]'
                ],
                'code_patterns': [
                    r'h\s*\(',  # Preact's createElement
                    r'Component\s+from\s+[\'"]preact[\'"]'
                ]
            },
            Framework.QWIK: {
                'dependencies': ['@builder.io/qwik'],
                'dev_dependencies': ['@builder.io/qwik-city'],
                'config_files': ['qwik.config.js'],
                'file_extensions': ['.tsx'],
                'import_patterns': [
                    r'from\s+[\'"]@builder\.io/qwik[\'"]',
                    r'import\s+\{[^}]*component\$[^}]*\}\s+from'
                ],
                'code_patterns': [
                    r'component\$\s*\(',
                    r'useSignal\s*\(',
                    r'useStore\s*\(',
                    r'\$\s*\('  # Qwik's lazy loading syntax
                ]
            },
            Framework.LIT: {
                'dependencies': ['lit', 'lit-element', '@lit/reactive-element'],
                'dev_dependencies': ['@lit/localize-tools'],
                'config_files': ['lit.config.js'],
                'file_extensions': ['.ts', '.js'],
                'import_patterns': [
                    r'from\s+[\'"]lit[\'"]',
                    r'from\s+[\'"]lit-element[\'"]',
                    r'import\s+\{[^}]*LitElement[^}]*\}\s+from'
                ],
                'code_patterns': [
                    r'extends\s+LitElement',
                    r'@customElement\s*\(',
                    r'@property\s*\(',
                    r'html`',
                    r'css`'
                ]
            },
            Framework.ALPINE: {
                'dependencies': ['alpinejs'],
                'dev_dependencies': [],
                'config_files': [],
                'file_extensions': ['.html'],
                'import_patterns': [
                    r'from\s+[\'"]alpinejs[\'"]',
                    r'Alpine\.data\s*\('
                ],
                'code_patterns': [
                    r'x-data\s*=',
                    r'x-show\s*=',
                    r'x-if\s*=',
                    r'x-for\s*=',
                    r'@click\s*=',
                    r'Alpine\.store\s*\('
                ]
            }
        }
    
    def detect_from_package_json(self, package_json_path: Path) -> List[FrameworkInfo]:
        """Detect frameworks from package.json"""
        detected = []
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            dependencies = package_data.get('dependencies', {})
            dev_dependencies = package_data.get('devDependencies', {})
            all_deps = {**dependencies, **dev_dependencies}
            
            for framework, patterns in self.framework_patterns.items():
                indicators = []
                
                # Check dependencies
                for dep in patterns['dependencies']:
                    if dep in dependencies:
                        indicators.append(f"dependency: {dep}@{dependencies[dep]}")
                
                # Check dev dependencies
                for dep in patterns['dev_dependencies']:
                    if dep in dev_dependencies:
                        indicators.append(f"devDependency: {dep}@{dev_dependencies[dep]}")
                
                if indicators:
                    # Try to get version from main package
                    version = None
                    for dep in patterns['dependencies']:
                        if dep in all_deps:
                            version = all_deps[dep]
                            break
                    
                    confidence = min(1.0, len(indicators) * 0.3)
                    detected.append(FrameworkInfo(
                        framework=framework,
                        version=version,
                        confidence=confidence,
                        indicators=indicators
                    ))
        
        except Exception as e:
            logger.error(f"Error reading package.json: {e}")
        
        return detected
    
    def detect_from_files(self, project_root: Path) -> List[FrameworkInfo]:
        """Detect frameworks from file patterns and config files"""
        detected = {}
        
        for framework, patterns in self.framework_patterns.items():
            indicators = []
            config_files = []
            
            # Check for config files
            for config_file in patterns['config_files']:
                if (project_root / config_file).exists():
                    config_files.append(config_file)
                    indicators.append(f"config: {config_file}")
            
            # Check for file extensions
            for ext in patterns['file_extensions']:
                files = list(project_root.rglob(f"*{ext}"))
                if files:
                    count = len(files)
                    indicators.append(f"files: {count} {ext} files")
            
            if indicators:
                if framework not in detected:
                    detected[framework] = FrameworkInfo(
                        framework=framework,
                        confidence=0.0,
                        indicators=[],
                        config_files=config_files
                    )
                
                detected[framework].indicators.extend(indicators)
                detected[framework].confidence = min(1.0, len(indicators) * 0.25)
        
        return list(detected.values())
    
    def detect_from_code(self, project_root: Path, sample_size: int = 10) -> List[FrameworkInfo]:
        """Detect frameworks from code patterns in source files"""
        detected = {}
        
        # Sample TypeScript and JavaScript files
        ts_files = list(project_root.rglob("*.ts"))[:sample_size]
        tsx_files = list(project_root.rglob("*.tsx"))[:sample_size]
        js_files = list(project_root.rglob("*.js"))[:sample_size]
        jsx_files = list(project_root.rglob("*.jsx"))[:sample_size]
        vue_files = list(project_root.rglob("*.vue"))[:sample_size]
        svelte_files = list(project_root.rglob("*.svelte"))[:sample_size]
        
        all_files = ts_files + tsx_files + js_files + jsx_files + vue_files + svelte_files
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for framework, patterns in self.framework_patterns.items():
                    matches = []
                    
                    # Check import patterns
                    for pattern in patterns['import_patterns']:
                        import re
                        if re.search(pattern, content):
                            matches.append(f"import pattern: {pattern}")
                    
                    # Check code patterns
                    for pattern in patterns['code_patterns']:
                        if re.search(pattern, content):
                            matches.append(f"code pattern: {pattern}")
                    
                    if matches:
                        if framework not in detected:
                            detected[framework] = FrameworkInfo(
                                framework=framework,
                                confidence=0.0,
                                indicators=[]
                            )
                        
                        detected[framework].indicators.extend([
                            f"{file_path.name}: {match}" for match in matches[:2]
                        ])
            
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        # Calculate confidence based on indicators
        for framework_info in detected.values():
            framework_info.confidence = min(1.0, len(framework_info.indicators) * 0.1)
        
        return list(detected.values())
    
    def detect(self, project_root: Path) -> Dict[str, Any]:
        """Detect all frameworks in a project"""
        project_root = Path(project_root)
        
        # Collect all detections
        all_detections = []
        
        # Check package.json
        package_json = project_root / "package.json"
        if package_json.exists():
            all_detections.extend(self.detect_from_package_json(package_json))
        
        # Check files and config
        all_detections.extend(self.detect_from_files(project_root))
        
        # Check code patterns
        all_detections.extend(self.detect_from_code(project_root))
        
        # Merge detections by framework
        merged = {}
        for detection in all_detections:
            if detection.framework not in merged:
                merged[detection.framework] = detection
            else:
                # Merge indicators and update confidence
                existing = merged[detection.framework]
                existing.indicators.extend(detection.indicators)
                existing.confidence = min(1.0, existing.confidence + detection.confidence * 0.5)
                if detection.version and not existing.version:
                    existing.version = detection.version
                existing.config_files.extend(detection.config_files)
        
        # Sort by confidence
        detected_frameworks = sorted(merged.values(), key=lambda x: x.confidence, reverse=True)
        
        # Determine primary framework
        primary = detected_frameworks[0] if detected_frameworks and detected_frameworks[0].is_high_confidence else None
        
        # Check if it's a hybrid project
        high_confidence_frameworks = [f for f in detected_frameworks if f.is_high_confidence]
        is_hybrid = len(high_confidence_frameworks) > 1
        
        return {
            'primary_framework': primary.framework.value if primary else Framework.VANILLA.value,
            'all_frameworks': [
                {
                    'name': f.framework.value,
                    'version': f.version,
                    'confidence': f.confidence,
                    'indicators': f.indicators[:5],  # Limit indicators
                    'config_files': f.config_files
                }
                for f in detected_frameworks
            ],
            'is_hybrid': is_hybrid,
            'detection_summary': {
                'has_package_json': package_json.exists(),
                'detected_count': len(detected_frameworks),
                'high_confidence_count': len(high_confidence_frameworks)
            }
        }


def detect_framework(project_root: str) -> Dict[str, Any]:
    """Convenience function to detect frameworks in a project"""
    detector = FrameworkDetector()
    return detector.detect(Path(project_root))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python framework_detector.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    result = detect_framework(project_root)
    
    print(f"\n=== Framework Detection Results ===")
    print(f"Primary Framework: {result['primary_framework']}")
    print(f"Is Hybrid Project: {result['is_hybrid']}")
    print(f"\nDetected Frameworks:")
    for fw in result['all_frameworks']:
        print(f"  - {fw['name']} (confidence: {fw['confidence']:.2f})")
        if fw['version']:
            print(f"    Version: {fw['version']}")
        if fw['indicators']:
            print(f"    Indicators: {', '.join(fw['indicators'][:3])}")