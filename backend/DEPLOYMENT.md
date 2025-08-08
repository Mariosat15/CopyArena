# CopyArena Backend Deployment

## Cloud Deployment (Render)

This backend is designed to work on both Windows (with real MT5) and Linux cloud servers (with mock MT5).

### Render Configuration

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. **Python Version**: 3.11
4. **Root Directory**: `backend`

### Environment Variables

The app automatically detects the environment:
- **Windows**: Uses real MetaTrader5 library
- **Linux (Cloud)**: Uses mock MT5 for demo purposes

### Mock MT5 Features

In cloud deployment, the app provides:
- Mock account information
- Simulated trade data
- Demo mode functionality
- Full API compatibility

This allows users to:
- Register and test the interface
- See how the app works
- Experience the UI/UX
- Connect their real MT5 when using local deployment

## Local Development

For real MT5 integration, run locally on Windows with:
```bash
pip install -r requirements.txt
python app.py
``` 