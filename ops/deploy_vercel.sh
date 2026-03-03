#!/bin/bash

# BalanceHub SaaS Portal - Vercel Deployment Automation (§4287)
# Built by HyperAI for the Autonomous Mesh.

echo "🚀 Starting Deployment Pulse for BalanceHub Portal..."

# 1. Build Verification
cd /Users/andy/balancehub/landing-page
echo "🏗️  Running industrial-grade build..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build Successful. Ready for Edge Deployment."
    echo "---------------------------------------------------"
    echo "💡 ACTION REQUIRED FROM MASTER:"
    echo "1. Ensure you have the Vercel CLI installed (npm i -g vercel)."
    echo "2. Run the following command in the current directory:"
    echo "   vercel --prod"
    echo "---------------------------------------------------"
    echo "🌐 Your Autonomous Portal will be live at balancehub.vercel.app (or custom domain)."
else
    echo "❌ Build failed. Check logs for semantic errors."
    exit 1
fi
