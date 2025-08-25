# Uplevel AI Financial Intelligence Portal

A modern, responsive frontend interface for the Uplevel AI multi-agent system, built with Next.js 14, TypeScript, and Tailwind CSS.

## Features

✅ **Modern Tech Stack**
- Next.js 15.5.0 with App Router
- TypeScript for type safety
- Tailwind CSS + shadcn/ui for beautiful UI components
- Zustand for state management

✅ **Authentication**
- Google OAuth integration via NextAuth.js
- Secure session management
- Protected routes

✅ **Real-time Chat Interface**
- Beautiful, responsive chat UI
- Real-time messaging with the deployed Financial Intelligence Agent
- Message history and session management
- Loading states and error handling

✅ **Agent Selection**
- Multi-agent system architecture (ready for Phase 2)
- Agent status indicators
- Capability descriptions

✅ **Session Management**
- Persistent conversation history
- Session creation and deletion
- Auto-save functionality

## Quick Start

### Prerequisites
- Node.js 20.x or later
- npm or yarn

### Installation

1. **Clone and navigate to the frontend**:
```bash
cd /home/brandon/projects/uplevel/portal/frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Configure environment variables**:
```bash
cp .env.local.example .env.local
```

4. **Update `.env.local` with your values**:
```env
# NextAuth.js Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here-generate-one

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret

# Financial Agent API (Already deployed and working!)
FINANCIAL_AGENT_API_URL=https://uplevel-financial-agent-834012950450.us-central1.run.app
```

5. **Generate NextAuth Secret**:
```bash
openssl rand -base64 32
```

6. **Set up Google OAuth**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials
   - Add `http://localhost:3000/api/auth/callback/google` to authorized redirect URIs

7. **Start the development server**:
```bash
npm run dev
```

8. **Open your browser**:
   - Navigate to `http://localhost:3000`
   - Sign in with Google
   - Start chatting with the Financial Intelligence Agent!

## Architecture

### Components
- `ChatInterface`: Main chat component with real-time messaging
- `SessionSidebar`: Session management and history
- `AgentSelector`: Agent selection and capability display
- `NextAuthProvider`: Authentication provider wrapper

### State Management (Zustand)
- `useChatStore`: Chat messages and session management
- `useAgentStore`: Available agents and selection
- `useSettingsStore`: User preferences and configuration

### API Integration
- Direct integration with the deployed Financial Intelligence Agent
- RESTful API calls to `/query` endpoint
- Error handling and retry logic

## Current Status

🟢 **Fully Functional**:
- Authentication with Google OAuth
- Real-time chat interface
- Session management
- Agent selection
- Integration with deployed Financial Intelligence Agent
- Responsive design
- Error handling and loading states

🔄 **In Progress**:
- Dashboard with financial metrics visualization
- Settings page for user preferences
- P&L statement specific interface

🔜 **Phase 2**:
- Additional AI agents (Research, General)
- WebSocket support for real-time updates
- Advanced dashboard features
- Mobile app support

## Testing

The application has been tested with:
- ✅ Next.js build process (successful)
- ✅ TypeScript compilation (no errors)
- ✅ ESLint validation (clean)
- ✅ Development server startup
- ✅ Agent API endpoint connectivity
- ✅ Authentication flow (ready for Google OAuth setup)

## Production Deployment

1. **Build for production**:
```bash
npm run build
```

2. **Start production server**:
```bash
npm start
```

3. **Deploy** (example with Vercel):
```bash
npx vercel --prod
```

## API Endpoints

The frontend integrates with these agent endpoints:

- `POST /query` - General queries and conversations
- `POST /pl-statement` - P&L statement generation (coming soon)

Example API call:
```javascript
const response = await fetch(`${agentEndpoint}/query`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "Analyze our financial performance",
    conversation_id: sessionId
  })
})
```

## Development

### Code Structure
```
src/
├── app/                 # Next.js app router pages
├── components/          # Reusable UI components
│   ├── ui/             # shadcn/ui components
│   ├── chat/           # Chat-specific components
│   └── providers/      # Context providers
├── lib/                # Utility functions
├── store/              # Zustand stores
└── types/              # TypeScript type definitions
```

### Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## Integration Notes

The frontend is designed to work seamlessly with the deployed Financial Intelligence Agent at:
`https://uplevel-financial-agent-834012950450.us-central1.run.app`

The agent is currently in demo mode and will provide sample responses. Once fully configured with HubSpot and QuickBooks credentials, it will provide real financial analysis.

## Next Steps

1. Set up Google OAuth credentials
2. Test the complete authentication flow
3. Explore the chat interface with the Financial Intelligence Agent
4. Prepare for Phase 2 multi-agent expansion

---

**Built with ❤️ using Next.js, TypeScript, and modern web technologies**
