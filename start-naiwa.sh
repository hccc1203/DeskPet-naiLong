#!/usr/bin/env bash
# 在 Linux（X11 / XWayland）上启动奶蛙桌宠。
#
# 用法：./start-naiwa.sh
# 依赖：已执行 npm ci，并安装 x11-utils 与 python3。
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

missing=()
for cmd in xset xwininfo xprop python3; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "缺少依赖：${missing[*]}" >&2
  echo "Ubuntu/Debian 可执行：sudo apt install x11-utils python3" >&2
  exit 1
fi

# 开机自启可能早于 XWayland 就绪，最多等待 10 秒。
for _ in {1..20}; do
  xset q >/dev/null 2>&1 && break
  sleep 0.5
done

electron=./node_modules/electron/dist/electron
if [ ! -x "$electron" ]; then
  echo "未找到 Electron，请先执行：npm ci" >&2
  exit 1
fi

electron_args=(--ozone-platform=x11)
sandbox_helper="$PWD/node_modules/electron/dist/chrome-sandbox"
if [ ! -u "$sandbox_helper" ] \
  || [ "$(stat -c '%u' "$sandbox_helper" 2>/dev/null || echo 1)" != "0" ]; then
  echo "提示：chrome-sandbox 未配置为 root 所有且 4755，本次使用 --no-sandbox 启动。" >&2
  electron_args+=(--no-sandbox)
fi

# Electron 的 skipTaskbar 仅支持 macOS/Windows。Linux 下发送 EWMH 消息，
# 让窗口管理器把桌宠与提醒浮层移出任务栏 / Ubuntu Dock。
hide_from_taskbar() {
  while true; do
    while read -r wid; do
      [ -n "$wid" ] || continue
      if ! xprop -id "$wid" _NET_WM_STATE 2>/dev/null \
        | grep -q _NET_WM_STATE_SKIP_TASKBAR; then
        python3 scripts/skip-taskbar.py "$wid" >/dev/null 2>&1 || true
      fi
    done < <(xwininfo -root -tree 2>/dev/null \
      | awk '/"(奶蛙桌宠|奶蛙提醒)"/{print $1}')
    sleep 2
  done
}

"$electron" "${electron_args[@]}" . &
app_pid=$!

hide_from_taskbar &
watcher_pid=$!

cleanup() {
  kill "$watcher_pid" 2>/dev/null || true
}
trap cleanup EXIT

wait "$app_pid" || true
