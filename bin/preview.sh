#!/usr/bin/env bash
# Start the local Washington Apple Pi WordPress preview and load the content.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker is not running. Start Docker and run this script again." >&2
  exit 1
fi

echo "Starting WordPress and the database..."
"${DC[@]}" up -d

echo "Waiting for WordPress files..."
for _ in $(seq 1 60); do
  if "${DC[@]}" exec -T wordpress test -f /var/www/html/wp-config.php; then
    break
  fi
  sleep 2
done

if ! "${DC[@]}" run --rm wpcli wp core is-installed >/dev/null 2>&1; then
  echo "Installing WordPress..."
  installed=0
  for _ in $(seq 1 20); do
    if "${DC[@]}" run --rm wpcli wp core install \
      --url="http://localhost:8080" \
      --title="THE PI" \
      --admin_user="pi-admin" \
      --admin_password="pi-preview" \
      --admin_email="office@wap.org" \
      --skip-email; then
      installed=1
      break
    fi
    sleep 3
  done
  if [ "$installed" -ne 1 ]; then
    echo "WordPress did not finish installing." >&2
    exit 1
  fi
fi

"${DC[@]}" run --rm wpcli wp theme activate washington-apple-pi
"${DC[@]}" run --rm wpcli wp rewrite structure '/%postname%/' --hard
"${DC[@]}" run --rm wpcli wp option update blogname "THE PI"
"${DC[@]}" run --rm wpcli wp option update blogdescription ""
"${DC[@]}" run --rm wpcli wp option update timezone_string "America/New_York"
"${DC[@]}" run --rm wpcli wp option update blog_public 0

if ! "${DC[@]}" run --rm wpcli wp option get wap_content_imported >/dev/null 2>&1; then
  echo "Loading pages, posts, menu, and captured media..."
  "${DC[@]}" run --rm wpcli wp eval-file /import/load-local.php
  "${DC[@]}" run --rm wpcli wp option update wap_content_imported 1
fi

FRONT="$("${DC[@]}" run --rm wpcli wp post list --post_type=page --name=home --field=ID)"
BLOG="$("${DC[@]}" run --rm wpcli wp post list --post_type=page --name=blog --field=ID)"
"${DC[@]}" run --rm wpcli wp option update show_on_front page
"${DC[@]}" run --rm wpcli wp option update page_on_front "$FRONT"
"${DC[@]}" run --rm wpcli wp option update page_for_posts "$BLOG"
MENU_ID="$("${DC[@]}" run --rm wpcli wp menu list --fields=term_id,name --format=csv | awk -F, 'NR>1 && $2=="Primary" { print $1; exit }')"
if [ -n "$MENU_ID" ]; then
  "${DC[@]}" run --rm wpcli wp menu location assign "$MENU_ID" primary
fi

LOGO_ID="$("${DC[@]}" run --rm wpcli wp theme mod get custom_logo 2>/dev/null || true)"
if [ -z "$LOGO_ID" ] || [ "$LOGO_ID" = "0" ]; then
  LOGO="$("${DC[@]}" run --rm wpcli wp media import /var/www/html/wp-content/themes/washington-apple-pi/assets/logo.jpg --title="THE PI" --porcelain)"
  "${DC[@]}" run --rm wpcli wp theme mod set custom_logo "$LOGO"
fi

echo
echo "Preview is ready: http://localhost:8080"
echo "Admin: http://localhost:8080/wp-admin  (user pi-admin, password pi-preview)"
echo "These credentials are only for this local evaluation copy."
