# Contributing to NEMO

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/nemo-ide.git`
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   cd dashboard && npm install && cd ..
   ```
4. Set up environment variables:
   ```powershell
   Copy-Item .env.example .env
   # Edit .env with your OPENROUTER_API_KEY
   ```

## Running Tests

```powershell
python -m pytest test_client_unit.py -q
```

## Pull Request Process

1. Create a branch from `main`: `git checkout -b feature/amazing-feature`
2. Make your changes and test locally
3. Commit with a descriptive message
4. Push to your fork: `git push origin feature/amazing-feature`
5. Open a Pull Request against the main branch

## License

By contributing, you agree that your contributions will be licensed under the MIT License.