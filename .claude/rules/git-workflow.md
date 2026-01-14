# Git Workflow

## Commit Messages

### Format
```
<type>: <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 (1M context) <noreply@anthropic.com>
```

### Types
- `feat:` — новая фича
- `fix:` — исправление бага
- `docs:` — обновление документации
- `refactor:` — рефакторинг без изменения поведения
- `test:` — добавление/изменение тестов
- `chore:` — техническая работа (deps, config)

### Examples
```bash
# Good
git commit -m "feat: add reward system based on @whysasha methodology"
git commit -m "fix: prevent double reward on morning kaizen"
git commit -m "docs: update CHANGELOG with reward system section"

# Bad
git commit -m "changes"
git commit -m "work in progress"
git commit -m "fix bug"  # Какой bug?
```

---

## Deployment

### Auto-deploy
```bash
git push  # → GitHub Actions → сервер 64.137.9.146
```

### Проверка деплоя
```bash
gh run list --limit 3
ssh root@64.137.9.146 "cd /root/kaizen-bot && git log -1 --oneline"
```

---

## Branch Strategy

### Main branch: master
- Всегда готов к деплою
- Прямые коммиты в master для личного проекта (no PRs needed)
- Rebase при конфликтах

### No feature branches needed
Это личный проект — коммитим прямо в master.

---

## Git Safety

### NEVER
- ❌ `git push --force` в master
- ❌ `git reset --hard` без понимания
- ❌ Коммитить `.env` файлы (есть pre-commit hook!)

### ALWAYS
- ✅ Проверяй `git status` перед коммитом
- ✅ Проверяй `git diff` перед коммитом
- ✅ Пуши сразу после коммита (чтобы не забыть)
