# Branch Protection Configuration

## Required Settings for `main` branch

Configure these settings in GitHub: Settings → Branches → Add rule

### Branch name pattern
```
main
```

### Protect matching branches

- [x] **Require a pull request before merging**
  - [x] Require approvals: 1
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners (optional)

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - Required status checks:
    - `Lint & Format`
    - `Tests (Python 3.11)`
    - `Tests (Python 3.12)`
    - `Build Docker`

- [x] **Require conversation resolution before merging**

- [ ] **Require signed commits** (optional)

- [ ] **Require linear history** (optional)

- [x] **Do not allow bypassing the above settings**

### Rules applied to everyone including administrators
- [x] Enabled

## Required Secrets

Configure in Settings → Secrets and variables → Actions:

| Secret | Description | Required |
|--------|-------------|----------|
| `RAILWAY_TOKEN` | Railway API token for deployment | Yes |
| `RAILWAY_APP_URL` | Deployed app URL (e.g., https://valerie-api.railway.app) | Yes |
| `CODECOV_TOKEN` | Codecov token for coverage reports | Optional |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |

## Environments

Configure in Settings → Environments:

### `production`
- Required reviewers: 1 (optional)
- Wait timer: 0 minutes
- Deployment branches: `main` only
- Environment secrets:
  - `RAILWAY_TOKEN`
  - `RAILWAY_APP_URL`

### `staging` (optional)
- No required reviewers
- Deployment branches: `develop`, `main`

## Workflow Permissions

Configure in Settings → Actions → General:

- Workflow permissions: **Read and write permissions**
- Allow GitHub Actions to create and approve pull requests: **Enabled**

## Creating a Release

1. Create and push a version tag:
   ```bash
   git tag v2.5.1
   git push origin v2.5.1
   ```

2. Or use the GitHub UI:
   - Go to Releases → Draft a new release
   - Create a new tag (e.g., v2.5.1)
   - Auto-generate release notes
   - Publish release

The release workflow will:
1. Run all tests
2. Build Docker images for linux/amd64 and linux/arm64
3. Push to GitHub Container Registry
4. Create GitHub release with changelog
5. Deploy to Railway production
