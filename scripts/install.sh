#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CODEX_HOME=${CODEX_HOME:-"$HOME/.codex"}
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_ROOT="$CODEX_HOME/backups/development-pipeline-v2-install-$TIMESTAMP"
ABSENT_FILE="$BACKUP_ROOT/absent-paths.txt"
OK=0

targets='skills/development-pipeline-v2/SKILL.md
skills/development-pipeline-v2/agents/openai.yaml
agents/dp-v2-implementer.toml
agents/dp-v2-reviewer.toml
agents/dp-v2-verifier.toml'

sha_or_absent() {
    if [ -L "$1" ]; then
        printf '%s\n' "SYMLINK"
    elif [ -f "$1" ]; then
        shasum -a 256 "$1" | awk '{print $1}'
    elif [ -e "$1" ]; then
        printf '%s\n' "OTHER"
    else
        printf '%s\n' "ABSENT"
    fi
}

protected_snapshot() {
    printf '%s\n' \
        "$(sha_or_absent "$CODEX_HOME/skills/development-pipeline/SKILL.md")" \
        "$(sha_or_absent "$CODEX_HOME/skills/development-pipeline/agents/openai.yaml")" \
        "$(sha_or_absent "$CODEX_HOME/config.toml")" \
        "$(sha_or_absent "$CODEX_HOME/AGENTS.md")"
}

rollback() {
    printf '%s\n' "$targets" | while IFS= read -r relative; do
        [ -n "$relative" ] || continue
        destination="$CODEX_HOME/$relative"
        backup="$BACKUP_ROOT/$relative"
        if [ -f "$backup" ]; then
            mkdir -p "$(dirname -- "$destination")"
            cp -p "$backup" "$destination"
        elif [ -f "$ABSENT_FILE" ] && grep -Fqx "$relative" "$ABSENT_FILE"; then
            rm -f "$destination"
        fi
    done
}

cleanup_on_exit() {
    if [ "$OK" -ne 1 ]; then
        rollback
        printf '%s\n' "Installation failed; restored pre-install state." >&2
    fi
}

trap cleanup_on_exit EXIT HUP INT TERM

python3 "$REPO_ROOT/scripts/validate.py"

if [ -e "$BACKUP_ROOT" ]; then
    printf '%s\n' "Backup path already exists: $BACKUP_ROOT" >&2
    exit 1
fi
mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
: > "$ABSENT_FILE"
chmod 600 "$ABSENT_FILE"

protected_before=$(protected_snapshot)

printf '%s\n' "$targets" | while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    source_file="$REPO_ROOT/$relative"
    destination="$CODEX_HOME/$relative"
    backup="$BACKUP_ROOT/$relative"
    if [ -L "$destination" ] || { [ -e "$destination" ] && [ ! -f "$destination" ]; }; then
        printf '%s\n' "Refusing non-regular target: $destination" >&2
        exit 1
    fi
    if [ -f "$destination" ]; then
        mkdir -p "$(dirname -- "$backup")"
        cp -p "$destination" "$backup"
        chmod 600 "$backup"
    else
        printf '%s\n' "$relative" >> "$ABSENT_FILE"
    fi
    mkdir -p "$(dirname -- "$destination")"
    temporary="$destination.tmp.$$"
    cp "$source_file" "$temporary"
    chmod 644 "$temporary"
    mv "$temporary" "$destination"
done

python3 "$REPO_ROOT/scripts/validate.py" --installed "$CODEX_HOME"

protected_after=$(protected_snapshot)
if [ "$protected_before" != "$protected_after" ]; then
    printf '%s\n' "Protected inputs changed during installation." >&2
    exit 1
fi

OK=1
trap - EXIT HUP INT TERM
printf '%s\n' "Installed five runtime files into $CODEX_HOME"
printf '%s\n' "Backup: $BACKUP_ROOT"
