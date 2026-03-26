# Contributing to InboxConverge

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and inclusive. We welcome contributions from everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/christianlouis/inboxconverge/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Relevant logs (remove sensitive info!)

### Suggesting Features

1. Check the [Roadmap](docs/ROADMAP.md) to see if it's already planned
2. Open an issue with the "enhancement" label
3. Describe the feature and its use case
4. Explain why it would be useful

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Run the test suite
   make test

   # Or run linting + formatting + tests together
   make quick-test

   # Test Docker build
   docker build -t pop3-test .
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add feature: brief description"
   ```
   
   Use clear, descriptive commit messages:
   - `Add feature: ...`
   - `Fix bug: ...`
   - `Update docs: ...`
   - `Improve performance: ...`

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request**
   - Describe what changes you made
   - Reference any related issues
   - Include screenshots for UI changes

## Development Setup

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/inboxconverge.git
cd inboxconverge

# Install all development dependencies
make install-dev

# Copy example config
cp .env.example .env
# Edit .env with test credentials

# Run the legacy forwarder script directly
python inbox_converge.py

# Or start the SaaS backend in dev mode
make run-dev
```

### Docker Development

```bash
# Build image
docker build -t pop3-dev .

# Run with your config
docker run --env-file .env pop3-dev
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Handle errors gracefully
- Run `make format` to auto-format with Black and Ruff

## Testing

Before submitting a PR:

1. **Run the test suite**
   ```bash
   make test
   ```

2. **Run linting**
   ```bash
   make lint
   ```

3. **Docker build**
   ```bash
   docker build -t pop3-test .
   ```

4. **Manual testing** (if applicable)
   - Test with a real POP3 account or mock
   - Verify emails are forwarded correctly
   - Check error handling
   - Review logs

## Documentation

Update documentation when:
- Adding new features
- Changing configuration options
- Modifying behavior
- Adding dependencies

Files to update:
- `README.md` - Main documentation
- `docs/QUICKSTART.md` - If setup changes
- `docs/MVP.md` - If MVP scope changes
- `docs/ROADMAP.md` - If adding future plans

## Security

- **Never commit credentials** or sensitive data
- Use environment variables for secrets
- Report security issues privately (see below)
- Follow security best practices

### Reporting Security Issues

**Do NOT open public issues for security vulnerabilities.**

Please see [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

## Questions?

- Open a discussion in GitHub Discussions
- Comment on relevant issues
- Ask in pull requests

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments section

Thank you for contributing! 🎉
