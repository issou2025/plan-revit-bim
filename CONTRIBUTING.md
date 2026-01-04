# Contributing to Plan Revit BIM

Thank you for your interest in contributing to this project! This document provides guidelines for contributing.

## Code of Conduct

Please be respectful and professional in all interactions related to this project.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Your environment (OS, Python version, browser)
- Screenshots if applicable

### Suggesting Enhancements

Enhancement suggestions are welcome! Please open an issue with:
- A clear, descriptive title
- Detailed description of the proposed enhancement
- Why this enhancement would be useful
- Any relevant examples or mockups

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test your changes thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

#### Pull Request Guidelines

- Keep changes focused and atomic
- Update documentation if needed
- Follow existing code style
- Add comments for complex logic
- Test your changes
- Update README if adding new features

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/issou2025/plan-revit-bim.git
   cd plan-revit-bim
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

5. Run the application:
   ```bash
   python app.py
   ```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Comment complex logic

## Testing

Before submitting a pull request:
- Test all functionality you've changed
- Test the application in different browsers
- Test on both desktop and mobile viewports
- Check that no errors appear in browser console
- Verify all forms work correctly

## Questions?

Feel free to open an issue for any questions or reach out to entreprise2rc@gmail.com.

Thank you for contributing!
