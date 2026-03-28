#!/bin/zsh
# Install Warp launch configurations, pablo:// URL scheme handler, and redirect server
# Run this on a fresh machine after cloning the openclaw repo

set -e

SKILL_DIR="$HOME/.openclaw/skills/launching-tasks"

echo "Installing Warp task launchers..."

# 1. Create Warp launch configurations directory
mkdir -p ~/.warp/launch_configurations

# 2. Copy launch configs
cp "$SKILL_DIR/configs/my-top-tasks.yaml" ~/.warp/launch_configurations/
cp "$SKILL_DIR/configs/todays-tasks.yaml" ~/.warp/launch_configurations/
echo "  Installed my-top-tasks.yaml"
echo "  Installed todays-tasks.yaml"

# 3. Install work-task.sh
mkdir -p ~/scripts
cp "$SKILL_DIR/scripts/work-task.sh" ~/scripts/work-task.sh
chmod +x ~/scripts/work-task.sh
echo "  Installed work-task.sh"

# 4. Build Pablo URL Handler app
APP_DIR="$HOME/Applications/Pablo URL Handler.app"
rm -rf "$APP_DIR"

osacompile -o "$APP_DIR" -e 'on open location theURL
  do shell script "/Users/" & (short user name of (system info)) & "/scripts/work-task.sh " & quoted form of theURL & " &>/dev/null &"
end open location'

# Add URL scheme to Info.plist
defaults write "$APP_DIR/Contents/Info" CFBundleURLTypes -array '<dict><key>CFBundleURLName</key><string>Pablo Task Handler</string><key>CFBundleURLSchemes</key><array><string>pablo</string></array></dict>'

echo "  Built Pablo URL Handler.app"

# 5. Register URL scheme with macOS
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -R "$APP_DIR"

# Open it once to ensure registration
open "$APP_DIR"
sleep 1

echo "  Registered pablo:// URL scheme"

# 6. Install pablo redirect server (http://localhost:19280 -> pablo://)
cp "$SKILL_DIR/scripts/pablo-redirect.py" ~/scripts/pablo-redirect.py
chmod +x ~/scripts/pablo-redirect.py
echo "  Installed pablo-redirect.py"

# 7. Install and load launchd agent
PLIST_NAME="com.pablo.redirect"
PLIST_SRC="$SKILL_DIR/configs/$PLIST_NAME.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Unload existing if present
launchctl bootout "gui/$(id -u)/$PLIST_NAME" 2>/dev/null || true

# Copy plist and fix the script path
sed "s|PLACEHOLDER_SCRIPT_PATH|$HOME/scripts/pablo-redirect.py|" "$PLIST_SRC" > "$PLIST_DST"

# Load the agent
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"

echo "  Started pablo redirect server on http://localhost:19280"

# 8. Clean up old config files
rm -f ~/.warp/launch_configurations/openclaw-tasks.yaml

echo ""
echo "Done! Launch configs:"
echo "  warp://launch/My%20Top%20Tasks"
echo "  warp://launch/Today's%20Tasks"
echo ""
echo "Task links (for Airtable, Warp, anywhere):"
echo "  http://localhost:19280/task/Your+Task+Title"
echo "  pablo://task/Your+Task+Title"
echo ""
echo "Test with:"
echo "  open \"http://localhost:19280/task/Test+Task\""
