# Production Configuration Guide

## Quick Start

### 1. Basic Configuration

Create a `.hallucination-detector.json` in your project root:

```json
{
  "external_modules": [
    "rxjs",
    "ramda", 
    "@emotion/styled",
    "@apollo/client",
    "your-internal-lib"
  ],
  "trusted_patterns": {
    "services": ["*Service", "*Manager", "*Provider"],
    "methods": ["get*", "set*", "fetch*", "handle*"]
  },
  "confidence_threshold": 0.8,
  "ignore_paths": [
    "node_modules/**",
    "dist/**",
    "*.generated.ts"
  ]
}
```

### 2. Environment-Specific Settings

```python
# In your validator_config.py or environment config
import os

# Development - More lenient
if os.getenv('NODE_ENV') == 'development':
    config.confidence_threshold = 0.9
    config.trust_internal_imports = True

# CI/CD - Stricter
elif os.getenv('CI'):
    config.confidence_threshold = 0.7
    config.fail_on_hallucination = True
```

### 3. Library-Specific Configuration

#### For RxJS Projects:
```python
NAMESPACE_METHODS['Observable'] = {
    'pipe', 'subscribe', 'next', 'complete', 'error',
    'map', 'filter', 'switchMap', 'mergeMap', 'tap'
}
```

#### For Functional Programming:
```python
NAMESPACE_METHODS['R'] = {  # Ramda
    'map', 'filter', 'reduce', 'pipe', 'curry',
    'compose', 'prop', 'path', 'evolve'
}
```

#### For GraphQL:
```python
EXTERNAL_MODULES.update({
    '@apollo/client', 'graphql', 'graphql-tag'
})
```

### 4. CI/CD Integration

#### GitHub Actions:
```yaml
- name: Check for hallucinations
  run: |
    python run_validation_tests.py --changed-files-only
  continue-on-error: true  # Warning mode
```

#### Pre-commit Hook:
```bash
#!/bin/bash
# .git/hooks/pre-commit
files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx|js|jsx)$')
if [ -n "$files" ]; then
  python check_hallucinations.py $files
fi
```

### 5. Custom Rules

```python
# Add to validator_config.py
class CustomValidatorConfig(ValidatorConfig):
    def is_trusted_pattern(self, pattern: str) -> bool:
        # Your company's patterns
        if pattern.startswith('use') and pattern.endswith('Query'):
            return True  # Custom hooks
        if pattern.match(r'^\$\w+'):  # jQuery-like
            return True
        return super().is_trusted_pattern(pattern)
```

### 6. Handling False Positives

#### Inline Suppression:
```typescript
// @hallucination-check-disable-next-line
dynamicObject[computedMethod]();  // Dynamic access

// @hallucination-check-disable-block
const meta = {
  [Symbol.for('custom')]: true,
  customPrototypeMethod() {}
};
// @hallucination-check-enable
```

#### File-Level Configuration:
```typescript
// @hallucination-check-config {"confidence_threshold": 0.95}
// For files with lots of metaprogramming
```

### 7. Monitoring and Metrics

```python
# Log detections for analysis
import json
from datetime import datetime

def log_detection(result):
    with open('hallucination_metrics.jsonl', 'a') as f:
        f.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'file': result['script_path'],
            'confidence': result['overall_confidence'],
            'count': len(result['hallucinations_detected'])
        }) + '\n')
```

### 8. Gradual Adoption

#### Phase 1: Warning Mode
```bash
# Just log, don't fail builds
python detect_hallucinations.py --warn-only
```

#### Phase 2: New Code Only
```bash
# Check only changed files
git diff main --name-only | xargs python detect_hallucinations.py
```

#### Phase 3: Full Enforcement
```bash
# Fail builds on hallucinations
python detect_hallucinations.py --strict
```

## Common Configurations by Project Type

### React SPA
```json
{
  "external_modules": [
    "react", "react-dom", "react-router-dom",
    "@tanstack/react-query", "@emotion/react"
  ],
  "trusted_patterns": {
    "hooks": ["use*"],
    "components": ["*Provider", "*Context"]
  }
}
```

### Node.js Backend
```json
{
  "platform": "node",
  "external_modules": [
    "express", "fastify", "@nestjs/core",
    "typeorm", "prisma", "@prisma/client"
  ],
  "trusted_patterns": {
    "services": ["*Service", "*Repository"],
    "middleware": ["*Middleware", "*Guard"]
  }
}
```

### Full-Stack Monorepo
```json
{
  "projects": {
    "packages/web/*": {
      "platform": "browser",
      "external_modules": ["react", "@mui/material"]
    },
    "packages/api/*": {
      "platform": "node",
      "external_modules": ["@nestjs/core", "typeorm"]
    },
    "packages/shared/*": {
      "platform": "universal"
    }
  }
}
```

## Troubleshooting

### High False Positive Rate?
1. Add missing libraries to `external_modules`
2. Check if using newer JS features
3. Configure service patterns
4. Increase confidence threshold

### Missing Real Hallucinations?
1. Decrease confidence threshold
2. Check for typos in configuration
3. Ensure Neo4j is populated
4. Review ignored patterns

### Performance Issues?
1. Use file filtering
2. Enable caching
3. Run in parallel
4. Check only changed files

Remember: The goal is to catch dangerous AI hallucinations while minimizing disruption to your workflow. Start lenient and gradually increase strictness as your team adapts.