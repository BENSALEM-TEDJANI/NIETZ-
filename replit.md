# Workspace

## Overview

pnpm workspace monorepo using TypeScript + Python Flask application.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)
- **Python**: Flask 3.x (Python 3.11)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

## VFD Store (Flask App)

Arabic RTL e-commerce site for industrial Inverter VFD products.

- **Location**: `artifacts/vfd-store/`
- **Entry**: `artifacts/vfd-store/app.py`
- **Templates**: `artifacts/vfd-store/templates/`
- **Port**: 5000
- **Run**: `cd artifacts/vfd-store && PORT=5000 python app.py`

### Pages
- `/` — Home page with product display
- `/order` — Order form (name, phone, wilaya, power rating)
- `/success` — Order confirmation page
- `/admin` — Admin panel showing all orders

### Notes
- Orders stored in memory (list in app.py) — resets on server restart
- All 58 Algerian wilayas included in dropdown
- Power options: 0.75 kW to 55 kW

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
