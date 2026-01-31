# V2 Hotfix Playbook

Use this flow for critical fixes on the V2 production line. New features go to V3 (main).

## 1) Create a hotfix branch from release/v2

```bash
git checkout release/v2
git pull
git checkout -b hotfix/v2-<short-desc>
```

## 2) Implement the fix and open a PR into release/v2

```bash
git add .
git commit -m "fix: <critical issue>"
git push -u origin hotfix/v2-<short-desc>
```

Open a PR to `release/v2`, get at least 1 approval, and ensure required checks pass.

## 3) Tag and release the hotfix on release/v2

```bash
git checkout release/v2
git pull
git tag v2.<minor>.<patch>
git push origin release/v2 --tags
```

## 4) Backport the fix into V3 (main)

```bash
git checkout main
git pull
git cherry-pick <commit_sha_from_release_v2>
git push
```

If multiple commits were in the PR, cherry-pick each commit or use a merge commit SHA.

