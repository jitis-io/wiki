#!/usr/bin/env bash

set -euo pipefail

readonly APP_DIR="${APP_DIR:-/workspace}"
readonly BENCH_DIR="${BENCH_DIR:-/home/runner/frappe-bench}"
readonly DB_HOST="${DB_HOST:-mariadb}"
readonly DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-root}"
readonly SITE_NAME="${SITE_NAME:-test_site}"
readonly WIKI_ONLY_SITE_NAME="${WIKI_ONLY_SITE_NAME:-wiki_test_site}"

readonly FRAPPE_COMMIT="6b450a166e076dd842e4db7ea0843f62881e62ac"
readonly ERPNEXT_COMMIT="7474d9e786277383de1242ab882f16856d17a9c9"

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
	--frappe-branch v16.51.0 \
	--python "$(command -v python)" \
	--skip-assets \
	--skip-redis-config-generation \
	"$BENCH_DIR"

cd "$BENCH_DIR"
test "$(git -C apps/frappe rev-parse HEAD)" = "$FRAPPE_COMMIT"

bench get-app --branch v16.50.0 --skip-assets erpnext https://github.com/frappe/erpnext.git
test "$(git -C apps/erpnext rev-parse HEAD)" = "$ERPNEXT_COMMIT"

ensure_source_ref
# Test the complete working tree, including uncommitted fixes. Keep it at
# Bench's expected depth: the upstream frontend imports ../../../../sites.
readonly WIKI_SOURCE_DIR="$BENCH_DIR/local-apps/wiki"
mkdir -p "$(dirname "$WIKI_SOURCE_DIR")"
# Keep the upstream link:../../frappe/ui dependency valid when the exact Wiki
# working tree is soft-linked from local-apps rather than cloned into apps.
ln -s "$BENCH_DIR/apps/frappe" "$BENCH_DIR/local-apps/frappe"
cp -a "$APP_DIR" "$WIKI_SOURCE_DIR"
bench get-app --skip-assets --soft-link wiki "$WIKI_SOURCE_DIR"
test "$(readlink -f apps/wiki)" = "$(readlink -f "$WIKI_SOURCE_DIR")"
bench setup requirements --dev
node "$APP_DIR/ci/smoke-node-security.cjs" "$WIKI_SOURCE_DIR/frontend"

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
bench --site "$WIKI_ONLY_SITE_NAME" run-tests --app wiki --test-category all
