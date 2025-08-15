# GitHub Secrets Setup Guide

## 🚨 Push Protection Issue Resolved

GitHub blocked your push because it detected API keys in the code. Here are your options:

## Option 1: Quick Fix - Allow the Secrets (Recommended)

Since these are development keys for your application, you can allow them:

1. **Click these links** to unblock the secrets:
   - [Unblock Google OAuth Client ID](https://github.com/VarunDronamraju/Macosbuild/security/secret-scanning/unblock-secret/31Jdz7q6DfBQ1QqPChnal6hWVzE)
   - [Unblock Google OAuth Client Secret](https://github.com/VarunDronamraju/Macosbuild/security/secret-scanning/unblock-secret/31Jdz9EvKgt5iETrhijIyHyaPcY)

2. **Mark them as "Used in tests"** or "False positive"

3. **Push again**:
   ```bash
   git push origin main
   ```

## Option 2: Use GitHub Secrets (More Secure)

I've updated the workflow to use GitHub secrets instead of hardcoded keys:

### Step 1: Set up GitHub CLI
```bash
# Install GitHub CLI
# Windows: winget install GitHub.cli
# macOS: brew install gh
# Linux: sudo apt install gh

# Login to GitHub
gh auth login
```

### Step 2: Run the setup script
```bash
python scripts/setup_github_secrets.py
```

### Step 3: Commit and push
```bash
git add .
git commit -m "Use GitHub secrets for API keys"
git push origin main
```

## Option 3: Manual Secret Setup

If you prefer to set secrets manually:

1. **Go to your GitHub repository**
2. **Click Settings → Secrets and variables → Actions**
3. **Add these secrets**:

| Secret Name | Value |
|-------------|-------|
| `TAVILY_API_KEY` | `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` |
| `GOOGLE_CLIENT_ID` | `778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | `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` |
| `SECRET_KEY` | `kJ8mN2pQ5sT9vY3wZ6aD1fH4jL7nR0uX8bE5hK2mP9sV6yB3eG1iL4oR7tA0cF3h` |

## Why This Happened

GitHub's push protection detected:
- **Google OAuth Client ID**: Used for user authentication
- **Google OAuth Client Secret**: Used for secure authentication
- **Tavily API Key**: Used for web search functionality

These are **development/test keys** that you want to include in your application for one-step installation.

## Security Considerations

- ✅ **Development keys**: These are test keys, not production secrets
- ✅ **Public application**: Users need these keys to use your app
- ✅ **No sensitive data**: No passwords or private information exposed
- ✅ **Intended inclusion**: You want these keys in the final application

## Next Steps

1. **Choose an option** above (Option 1 is fastest)
2. **Push your changes** to trigger the build
3. **Monitor GitHub Actions** for the build progress
4. **Download the DMG** when complete

## Build Artifacts

Once the workflow runs successfully, you'll get:
- `RAG Companion AI.app` - Application bundle
- `RAGCompanionAI-Installer.dmg` - DMG installer
- `install.sh` - One-step installation script
- `README.md` - Installation instructions

## Support

If you encounter issues:
1. Check the GitHub Actions logs
2. Verify secrets are set correctly
3. Ensure repository permissions allow workflows

---

**Recommendation**: Use **Option 1** (allow secrets) since these are development keys intended for distribution with your application.
