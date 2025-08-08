# CopyArena - Gamified Copy Trading Platform

CopyArena is a revolutionary gamified copy trading platform that transforms retail trading by combining social copy trading with gaming mechanics and AI-powered analytics. The platform connects to users' MT4/MT5 platforms for real-time trading activity, social following, and performance rewards.

## 🚀 Features

### Core Features
- **MT4/MT5 Integration**: Direct connection to trading platforms via WebSocket
- **Copy Trading System**: Manual and automated copy trading with risk management
- **Real-time Status**: Live online/offline indicators for all traders
- **AI-Powered Reports**: Advanced analytics and insights using OpenAI
- **Gamification**: XP points, levels, badges, and achievements
- **Social Trading**: Follow traders, view performance, and copy strategies

### User Roles
- **Traders**: Connect MT4/MT5 and allow others to copy their trades
- **Followers**: Browse and copy successful traders' strategies
- **Spectators**: Free users can view leaderboards and basic stats

### Monetization
- **Subscription Plans**: Free, Pro, and Elite tiers
- **Credits System**: Purchase credits for AI reports and premium features
- **Stripe Integration**: Secure payment processing

## 🛠️ Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **ShadCN UI** components
- **Zustand** for state management
- **Socket.IO** for real-time communication
- **Stripe** for payments

### Backend
- **FastAPI** (Python) for REST API
- **WebSocket** support for real-time data
- **SQLAlchemy** with SQLite/PostgreSQL
- **Stripe** for payment processing
- **OpenAI** for AI report generation
- **JWT** authentication

## 📦 Installation

### Prerequisites
- Node.js 18+
- Python 3.9+
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd copyarena
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Setup environment variables
cp ../.env.example .env
# Edit .env with your API keys and configuration

# Run the backend
python app.py
```

### 3. Frontend Setup
```bash
# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Run the frontend
npm run dev
```

### 4. Start Both Services
```bash
# Run both frontend and backend
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database
DATABASE_URL=sqlite:///./name of the database

# JWT
JWT_SECRET=your-jwt-secret-key

# Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Frontend
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
VITE_API_URL=http://localhost:8000
```

### Stripe Setup
1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe dashboard
3. Set up webhook endpoints for subscription management
4. Configure product/price IDs for subscription plans

### OpenAI Setup
1. Create an OpenAI account at https://openai.com
2. Generate an API key
3. Add the key to your environment variables

## 🎮 Gamification System

### XP Points & Levels
- Earn 10 XP per $1 USD profit
- Level up formula: `level = floor(sqrt(xp / 100)) + 1`
- Visual progress indicators and celebrations

### Badges & Achievements
- **Green Streak**: 3 profitable days in a row
- **Survivor**: 30 days without account wipe
- **Copy Magnet**: 50+ followers
- More badges unlock with different achievements

### Leaderboards
- Sort by XP points, total profit, or followers
- Real-time rankings with visual rank indicators
- Top 3 positions highlighted with special styling

## 💳 Subscription Plans

### Free Plan
- View leaderboard and marketplace
- No copy trading or AI reports
- Basic access only

### Pro Plan ($X/month)
- Copy trading unlocked
- Monthly credit allowance
- Standard AI reports

### Elite Plan ($XX/month)
- Premium copy trading features
- Advanced AI reports
- More credits and exclusive features

## 🔌 MT4/MT5 Integration

The platform requires a custom bridge plugin for MT4/MT5 that:
1. Connects securely to CopyArena via WebSocket
2. Streams real-time account status and trade data
3. Handles trade execution for copy trading
4. Maintains encrypted connections with token authentication

## 🛡️ Security Features

- JWT token authentication
- Encrypted MT4/MT5 connections
- Rate limiting and abuse prevention
- Stripe webhook verification
- Data anonymization for viewers

## 📊 AI Reports

The AI system analyzes:
- Trader performance metrics
- Risk-reward ratios
- Strategy consistency
- Market correlation
- Profit simulation models

## 🚀 Deployment

### Production Deployment
1. Set up PostgreSQL database
2. Configure production environment variables
3. Build the frontend: `npm run build`
4. Deploy backend with proper ASGI server (uvicorn)
5. Set up reverse proxy (nginx)
6. Configure SSL certificates

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the development team
- Check the documentation wiki

## 🛣️ Roadmap

- [ ] Mobile app development
- [ ] Advanced charting integration
- [ ] Multi-broker support
- [ ] Social media integration
- [ ] Advanced AI features
- [ ] Referral system
- [ ] Mobile notifications
- [ ] Advanced risk management tools

---

**CopyArena** - Revolutionizing retail trading through gamification and social features. 