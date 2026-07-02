# Local Development: Windows 11 + WSL2 Ubuntu + Cursor

## Rule of thumb

Use Windows for the editor window and WSL2 Ubuntu for the project runtime.

Work in:

```bash
~/dev/booklens
```

Do not work directly in:

```bash
/mnt/c/Users/...
```

## One-time WSL setup

```bash
sudo apt update
sudo apt install -y git make curl build-essential
```

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

Install Node through `nvm`:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
```

## Verify paths

From the repo root, run:

```bash
make check-env
```

Or manually:

```bash
which node
which npm
which python
which uv
which git
```

Good paths:

```text
~/.nvm/...
/usr/bin/...
~/.local/bin/...
```

Bad paths:

```text
/mnt/c/Program Files/...
/mnt/c/Users/...
```

## Open in Cursor

1. Install Cursor on Windows.
2. Use Cursor's WSL integration.
3. Open the folder from WSL, such as `~/dev/booklens`.
4. Use Cursor's integrated terminal while attached to WSL.

## Python pipeline commands

```bash
uv sync
make pipeline-demo
```

Small live test:

```bash
make pipeline-live CONTACT=you@example.com
```

## Web commands

```bash
make web-install
make web-dev
```

The web app lives in:

```text
apps/web
```

## If Next.js binaries break

If `node_modules/.bin/next` becomes a regular file instead of a symlink/executable, assume Windows npm polluted the install.

Fix:

```bash
cd apps/web
rm -rf node_modules package-lock.json
npm install
```

Run that from WSL only.
