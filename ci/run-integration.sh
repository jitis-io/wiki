#!/usr/bin/env bash

set -euo pipefail

readonly APP_DIR="${APP_DIR:-/workspace}"
readonly BENCH_DIR="${BENCH_DIR:-/home/runner/frappe-bench}"
readonly DB_HOST="${DB_HOST:-mariadb}"
readonly DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-root}"
readonly SITE_NAME="${SITE_NAME:-test_site}"
readonly WIKI_ONLY_SITE_NAME="${WIKI_ONLY_SITE_NAME:-wiki_test_site}"

readonly FRAPPE_COMMIT="5cba016e86b54b57f34a3864282b92300ef20fb0"
readonly ERPNEXT_COMMIT="b24c9eba551905e256e336ff170a91a92d197a2f"

mysql_ready() {
	mariadb-admin ping \
		--host="$DB_HOST" \
		--user=root \
		--password="$DB_ROOT_PASSWORD" \
		--silent
}

ensure_source_ref() {
	if git -C "$APP_DIR" rev-parse --git-dir >/dev/null 2>&1 \
		&& ! git -C "$APP_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
		git -C "$APP_DIR" \
			-c user.name="JITIS CI" \
			-c user.email="ci@example.invalid" \
			commit --quiet --allow-empty --message="ci: create disposable source ref"
	fi
}

until mysql_ready; do
	sleep 2
done

redis-server --daemonize yes --port 13000 --save "" --appendonly no
redis-server --daemonize yes --port 11000 --save "" --appendonly no

bench init \
	--frappe-branch v16.32.0 \
	--python "$(command -v python)" \
	--skip-assets \
	--skip-redis-config-generation \
	"$BENCH_DIR"

cd "$BENCH_DIR"
test "$(git -C apps/frappe rev-parse HEAD)" = "$FRAPPE_COMMIT"

bench get-app --branch v16.33.0 --skip-assets erpnext https://github.com/frappe/erpnext.git
test "$(git -C apps/erpnext rev-parse HEAD)" = "$ERPNEXT_COMMIT"

ensure_source_ref
bench get-app --skip-assets wiki "$APP_DIR"
bench setup requirements --dev

bench new-site \
	--db-host "$DB_HOST" \
	--db-root-username root \
	--db-root-password "$DB_ROOT_PASSWORD" \
	--admin-password admin \
	--install-app erpnext \
	"$SITE_NAME"

bench --site "$SITE_NAME" install-app wiki
bench --site "$SITE_NAME" migrate
bench build --app wiki
bench --site "$SITE_NAME" set-config allow_tests true
bench --site "$SITE_NAME" run-tests --app wiki --module wiki.test_privacy
bench --site "$SITE_NAME" run-tests --app wiki --module wiki.test_permissions
bench --site "$SITE_NAME" run-tests --app wiki --module wiki.test_read_protection
bench --site "$SITE_NAME" run-tests --app wiki --module wiki.test_search_compatibility

# Frappe's v16 test-record compatibility loader traverses every installed
# ERPNext DocType and expects optional ERPNext applications that are not part of
# this pinned stack. Run the complete Wiki suite on a second clean Frappe site,
# while the ERPNext site above remains the explicit cross-app compatibility gate.
bench new-site \
	--db-host "$DB_HOST" \
	--db-root-username root \
	--db-root-password "$DB_ROOT_PASSWORD" \
	--admin-password admin \
	"$WIKI_ONLY_SITE_NAME"
bench --site "$WIKI_ONLY_SITE_NAME" install-app wiki
bench --site "$WIKI_ONLY_SITE_NAME" migrate
bench --site "$WIKI_ONLY_SITE_NAME" set-config allow_tests true
bench --site "$WIKI_ONLY_SITE_NAME" run-tests --app wiki
