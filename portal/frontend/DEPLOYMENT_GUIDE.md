# Uplevel AI Frontend - Production Deployment Guide

## Quick Deploy to Vercel

### 1. Connect to GitHub Repository
```bash
npx vercel --prod
```

### 2. Set Production Environment Variables
In Vercel dashboard, add these environment variables:

```
NEXTAUTH_URL=https://your-domain.vercel.app
NEXTAUTH_SECRET=your-secure-secret-key-here
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
FINANCIAL_AGENT_API_URL=https://uplevel-financial-agent-834012950450.us-central1.run.app
SALES_AGENT_API_URL=https://uplevel-sales-agent-production.us-central1.run.app
ORCHESTRATOR_API_URL=https://uplevel-orchestrator-834012950450.us-central1.run.app
DEVELOPMENT_MODE=false
NEXT_PUBLIC_DEVELOPMENT_MODE=false
```

### 3. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth 2.0 credentials
3. Add authorized redirect URI: `https://your-domain.vercel.app/api/auth/callback/google`
4. Update environment variables with real credentials

### 4. Deploy Sales Agent to Cloud Run
```bash
cd ../../agents/sales_marketing
# Build and deploy to Cloud Run
# Update SALES_AGENT_API_URL with actual production URL
```

## Alternative: Deploy to Netlify

```bash
npm run build
# Upload dist folder to Netlify
# Configure environment variables in Netlify dashboard
```

## Development Mode (Current)
- Frontend: http://localhost:3000 ✅
- Authentication: Bypassed for development ✅ 
- APIs: Connected to production services ✅

## Production Checklist
- [ ] Deploy frontend to Vercel/Netlify
- [ ] Set up Google OAuth credentials  
- [ ] Deploy Sales Agent to Cloud Run
- [ ] Update all production URLs
- [ ] Test end-to-end functionality
- [ ] Enable SSL/HTTPS
- [ ] Configure custom domain (optional)

The system is ready for production deployment!
