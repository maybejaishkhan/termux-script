#!/data/data/com.termux/files/usr/bin/bash
# AutoGit Termux one-shot setup.
# Run: curl -L -O https://raw.githubusercontent.com/autogit-app/autogit/main/scripts/termux_setup.sh && bash termux_setup.sh
# Or:  curl -L https://raw.githubusercontent.com/autogit-app/autogit/main/scripts/termux_setup.sh | bash

set -e
REPO_RAW="${REPO_RAW:-https://raw.githubusercontent.com/autogit-app/autogit/main}"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}=== AutoGit Termux setup ===${NC}\n"

echo -e "${YELLOW}[1/4] Installing git and python...${NC}"
pkg update -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" > /dev/null 2>&1 || true
pkg install -y git python > /dev/null 2>&1
echo -e "${GREEN}    Done.${NC}\n"

echo -e "${YELLOW}[2/4] Downloading AutoGit Git Server script to ~/termux_git_server.py ...${NC}"
curl -L -s -o "$HOME/termux_git_server.py" "$REPO_RAW/scripts/termux_git_server.py"
if [ ! -f "$HOME/termux_git_server.py" ]; then
  echo -e "${RED}    Failed to download. Check your connection and REPO_RAW.${NC}"
  exit 1
fi
echo -e "${GREEN}    Done.${NC}\n"

echo -e "${YELLOW}[3/4] Setting server to run when Termux opens (~/.bashrc)...${NC}"
LINE='[ -f "$HOME/termux_git_server.py" ] && nohup python3 "$HOME/termux_git_server.py" >> "$HOME/autogit_git_server.log" 2>&1 &'
if grep -q 'termux_git_server.py' "$HOME/.bashrc" 2>/dev/null; then
  echo -e "${GREEN}    Already in .bashrc.${NC}\n"
else
  echo "$LINE" >> "$HOME/.bashrc"
  echo -e "${GREEN}    Done.${NC}\n"
fi

echo -e "${YELLOW}[4/4] Starting the server now...${NC}"
nohup python3 "$HOME/termux_git_server.py" >> "$HOME/autogit_git_server.log" 2>&1 &
sleep 1
if pgrep -f "termux_git_server.py" > /dev/null 2>&1; then
  echo -e "${GREEN}    Server is running.${NC}\n"
else
  echo -e "${RED}    Server may have failed to start. Check: cat ~/autogit_git_server.log${NC}\n"
fi

echo -e "${BOLD}${GREEN}=== Setup complete ===${NC}"
echo -e "Open the AutoGit app and use Local Repositories."
echo -e "Next time you open Termux, the server will start automatically."
echo -e "Log file: ${BLUE}~/autogit_git_server.log${NC}"
