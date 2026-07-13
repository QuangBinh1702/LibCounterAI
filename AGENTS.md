# Agent Instructions

## Project Skills

Use `.codex/skills/harness-intake-griller/SKILL.md` when a request needs
discussion, feature intake, docs, or story shaping before Symphony execution.
The skill is project-scoped; do not use a global copy as the source of truth.

<!-- HARNESS:BEGIN -->
## Harness

This repo uses Harness. Before work, read:

- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTEXT_RULES.md`
- `docs/TOOL_REGISTRY.md`
- `scripts/bin/harness-cli query matrix` on macOS/Linux, or `.\scripts\bin\harness-cli.exe query matrix` on Windows

Use the Rust Harness CLI at `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows as the main operational tool. Before a
step that could use an external tool, run `scripts/bin/harness-cli query tools
--capability <name> --status present` to see what is equipped; an absent
capability is a clean skip.
<!-- HARNESS:END -->

## Database Safety

**NEVER** run these commands — they destroy PostgreSQL data permanently:
- `docker-compose down -v`
- `docker volume rm` (any volume name)
- Any `-v` / `--volumes` flag with `docker-compose down` or `docker stack rm`

DB uses a named Docker volume `libcounterai_postgres_data`. Data survives
container/service/OS restart. A volume delete (the commands above) is the only
way data is lost — prohibit it.

## Git Discipline

**Chỉ được commit/push/pull khi tôi yêu cầu.** Không tự ý thực hiện bất kỳ
thao tác git nào. Nếu tôi kêu commit thì mới commit, kêu push thì mới push.

## Commit Convention

**1 feature = 1 commit.** Sau mỗi feature hoàn chỉnh, tôi sẽ đề xuất commit
gom tất cả file liên quan (code + test + docs + story packet + evidence) vào
chung 1 commit. Không tách code, docs, tests thành nhiều commit riêng cho cùng
1 feature. Timestamp luôn kèm trong commit message (VD: `2026-07-13`).
