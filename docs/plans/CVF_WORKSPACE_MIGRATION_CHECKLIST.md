# CVF Workspace Migration Checklist

## CVF Traceability
- CVF-Doc-ID: CVF-TT-MIG-20260302-R1
- Last-Updated: 2026-03-02
- Purpose: Move `Trading-Tools` into a controlled workspace alongside CVF safely.

## Recommendation (Important)
- Preferred: **clone CVF and Trading-Tools as sibling repositories** under one parent folder.
- Avoid: copying/moving `Trading-Tools` *inside* CVF git repo directly (causes git history and control issues).

Suggested layout:
- `D:\Work\.Controlled-Vibe-Framework-CVF`
- `D:\Work\Trading-Tools`

## Workspace Isolation Rule (Locked)
- Khi clone CVF, bắt buộc dùng thư mục có tiền tố dấu chấm:
  - `D:\Work\.Controlled-Vibe-Framework-CVF`
- Mục đích: tách biệt vận hành với `Trading-Tools`, giảm rủi ro thao tác nhầm.
- Đây là quy ước **cách ly workspace**, không nhằm mục tiêu ẩn thư mục.
- Khi phát triển Trading-Tools, luôn mở terminal/IDE root tại:
  - `D:\Work\Trading-Tools`
- Không chạy lệnh build/test/patch của Trading-Tools khi cwd đang ở CVF repo.

## Why clone is better
- Keeps independent git history and release flow.
- Easier to pin CVF version without polluting Trading-Tools history.
- Cleaner rollback and upgrade path.
- Supports controlled integration via docs/scripts, not ad-hoc file moves.

## Pre-Move Checklist
1. Ensure current branch is clean:
   - `git status --short` should be empty or intentionally committed.
2. Push current work to remote.
3. Create a safety tag:
   - `git tag pre-cvf-workspace-move-20260302`
   - `git push origin pre-cvf-workspace-move-20260302`
4. Backup local runtime artifacts if needed:
   - `.env`
   - `data/` (DuckDB and caches)
   - custom model folders
5. Record toolchain versions:
   - `python --version`
   - `uv --version`
   - `node -v`
   - `pnpm -v`

## Workspace Setup (Preferred)
1. Create parent folder (example):
   - `D:\Work`
2. Clone CVF:
   - `git clone https://github.com/Blackbird081/Controlled-Vibe-Framework-CVF.git "D:\Work\.Controlled-Vibe-Framework-CVF"`
3. Clone Trading-Tools:
   - `git clone https://github.com/Blackbird081/Trading-Tools.git "D:\Work\Trading-Tools"`
4. Keep both repos separate, then connect via:
   - documentation links,
   - shared checklists,
   - optional scripts referencing sibling path.

## If you must move existing folder
1. Move only repository directory, do not merge repos.
2. Re-open terminal in new path and verify:
   - `git rev-parse --show-toplevel`
   - `git remote -v`
3. Re-run installs:
   - backend deps (`uv sync`)
   - frontend deps (`pnpm -C frontend install`)
4. Re-validate env path assumptions in scripts.

## Post-Move Validation
1. Backend smoke:
   - start API server successfully
   - `/api/health` returns expected status
2. Frontend smoke:
   - app loads
   - dashboard data load works
   - market board renders
3. Trading smoke:
   - order form validation works
   - screener run endpoint reachable
4. Save migration log in `docs/plans` with:
   - date/time,
   - new path,
   - issues/fixes.

## Optional Controlled Integration Patterns
- Pattern A (recommended): sibling repos + shared process docs.
- Pattern B: add CVF as git submodule in Trading-Tools (pin exact CVF commit).
- Pattern C: monorepo merge (not recommended now; high risk, high overhead).

## Do-Not List
- Do not paste Trading-Tools files directly into CVF repository root.
- Do not rewrite git history during migration.
- Do not move without push/tag backup.
- Do not run Trading-Tools scripts/commands from `D:\Work\.Controlled-Vibe-Framework-CVF`.
