# Contributing to Speech Annotation Workbench

Thank you for considering contributing to the Speech Annotation Workbench! We welcome contributions from the community.

## Code of Conduct

Be respectful, inclusive, and considerate. We're building this together.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** first to avoid duplicates
2. **Use the bug report template** if available
3. **Include details**:
   - Operating system and version
   - Python version
   - FFmpeg version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and stack traces
   - Screenshots if applicable

### Suggesting Features

1. **Check existing feature requests** first
2. **Explain the use case** clearly
3. **Describe the proposed solution**
4. **Consider alternatives** you've thought about
5. **Be open to discussion**

### Submitting Code

#### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/inboxpraveen/Speech-Annotation-Workbench.git
cd Speech-Annotation-Workbench

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black flake8 mypy
```

#### Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**:
   - Write clean, readable code
   - Follow PEP 8 style guide
   - Add docstrings to functions and classes
   - Update documentation if needed

3. **Test your changes**:
   ```bash
   # Run the application
   python app.py
   
   # Manual testing in browser
   # Open http://localhost:5000
   
   # Run tests (when available)
   pytest tests/ -v
   ```

4. **Format and lint**:
   ```bash
   # Format code
   black asr_tool/ --line-length 100
   
   # Check linting
   flake8 asr_tool/ --max-line-length 100 --exclude=__pycache__
   
   # Type checking (optional but encouraged)
   mypy asr_tool/ --ignore-missing-imports
   ```

5. **Commit your changes**:
   ```bash
   # Use conventional commits format
   git add .
   git commit -m "feat: add new feature"
   # or
   git commit -m "fix: resolve bug with transcription"
   # or
   git commit -m "docs: update README with new instructions"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub.

#### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, no logic change)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:
```
feat: add real-time progress tracking for jobs
fix: resolve issue with locked records not saving
docs: update installation instructions for Windows
refactor: simplify audio processing pipeline
```

### Code Style Guidelines

#### Python

1. **Follow PEP 8** with these specifics:
   - Max line length: 100 characters
   - Use 4 spaces for indentation
   - Use type hints where possible

2. **Naming conventions**:
   - `snake_case` for functions and variables
   - `PascalCase` for classes
   - `UPPER_CASE` for constants
   - Prefix private methods with `_`

3. **Docstrings**:
   ```python
   def example_function(param1: str, param2: int) -> bool:
       """
       Brief description of what the function does.
       
       Args:
           param1: Description of param1
           param2: Description of param2
       
       Returns:
           Description of return value
       
       Raises:
           ValueError: When param1 is empty
       """
       pass
   ```

4. **Imports**:
   - Standard library imports first
   - Third-party imports second
   - Local imports last
   - Alphabetical within each group

   ```python
   import os
   from pathlib import Path
   
   import pandas as pd
   from flask import Flask
   
   from asr_tool.config import Config
   ```

#### JavaScript

1. **Use ES6+ features**:
   - `const` and `let` (no `var`)
   - Arrow functions
   - Template literals
   - Classes

2. **Naming conventions**:
   - `camelCase` for functions and variables
   - `PascalCase` for classes
   - `UPPER_CASE` for constants

3. **Documentation**:
   ```javascript
   /**
    * Brief description of function
    * @param {string} param1 - Description
    * @param {number} param2 - Description
    * @returns {boolean} Description
    */
   function exampleFunction(param1, param2) {
       // Implementation
   }
   ```

### Testing Guidelines

When adding new features, include tests:

```python
# tests/test_audio.py
def test_audio_conversion():
    """Test that audio files are converted to WAV correctly."""
    # Arrange
    source = Path("test_data/sample.mp3")
    job_id = "test-123"
    
    # Act
    result = convert_to_wav(source, job_id)
    
    # Assert
    assert result.exists()
    assert result.suffix == ".wav"
    
    # Cleanup
    result.unlink()
```

### Documentation

When adding features, update:

1. **README.md** - High-level usage changes
2. **PROJECT_DOCUMENTATION.md** - Technical details, API changes
3. **Code docstrings** - Function/class documentation
4. **This file** - Contributing process changes

### Pull Request Checklist

Before submitting:

- [ ] Code follows style guidelines
- [ ] Formatted with Black
- [ ] Linted with flake8 (no errors)
- [ ] All existing tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow conventional format
- [ ] Branch is up to date with `main`
- [ ] PR description explains changes clearly

### Review Process

1. **Automated checks** run on all PRs
2. **Maintainer review** - expect feedback and discussion
3. **Changes requested** - address feedback and update PR
4. **Approval** - maintainer approves
5. **Merge** - maintainer merges when ready

### Getting Help

- **GitHub Issues**: Ask questions, report bugs
- **Discussions**: General questions and ideas
- **Documentation**: Check PROJECT_DOCUMENTATION.md first

## Project Structure

Understanding the codebase:

```
asr_tool/
├── __init__.py          # Flask app factory
├── config.py            # Configuration management
├── routes.py            # API endpoints
└── services/            # Business logic
    ├── audio.py         # Audio processing
    ├── model.py         # ML model management
    ├── storage.py       # Data persistence
    └── job_manager.py   # Background jobs
```

### Key Concepts

1. **Services Layer**: All business logic lives in `services/`
2. **Routes Layer**: HTTP endpoints in `routes.py`, minimal logic
3. **Background Jobs**: Threading-based, managed by `job_manager.py`
4. **CSV Storage**: Simple persistence, thread-safe with locks
5. **FFmpeg Integration**: Subprocess calls for audio processing

## Feature Ideas

Looking for something to work on? Consider:

- [ ] Add SQLite/PostgreSQL storage backend
- [ ] Implement user authentication
- [ ] Add batch operations (bulk lock/unlock)
- [ ] Speaker diarization support
- [ ] Custom model training interface
- [ ] WebSocket real-time updates
- [ ] Docker Compose setup
- [ ] Kubernetes deployment templates
- [ ] API documentation with Swagger
- [ ] Unit test coverage improvements
- [ ] Performance benchmarking tools

## Questions?

Don't hesitate to ask! Open an issue at [https://github.com/inboxpraveen/Speech-Annotation-Workbench/issues](https://github.com/inboxpraveen/Speech-Annotation-Workbench/issues)

---

**Thank you for contributing!** 🎉
