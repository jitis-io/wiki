import { expect, test } from '../fixtures';
import { uniqueRoute } from '../helpers/factory';
import { createDoc, getDoc } from '../helpers/frappe';
import { SPACE_URL_RE, appUrl } from '../helpers/routes';

for (const publicSpace of [false, true]) {
	test(
		publicSpace
			? 'a space is public only after explicitly unchecking portal protection'
			: 'a new customer space is private before portal configuration',
		async ({ page, request, playwright, baseURL, wiki }) => {
			const route = uniqueRoute(publicSpace ? 'public' : 'private');
			await page.goto(appUrl('spaces'));
			await page.getByRole('button', { name: 'New Space' }).click();
			const dialog = page.getByRole('dialog');
			const protection = dialog.getByRole('checkbox', {
				name: 'Customer portal only',
			});
			await expect(protection).toBeChecked();
			if (publicSpace) await protection.uncheck();
			await dialog.getByLabel('Space Name').fill(route);
			await dialog
				.getByRole('textbox', { name: 'Route (required)', exact: true })
				.fill(route);
			await dialog.getByRole('button', { name: 'Create', exact: true }).click();
			await expect(page).toHaveURL(SPACE_URL_RE);
			const spaceId = page.url().split('/spaces/')[1].split(/[/?#]/)[0];
			wiki.adopt(spaceId);
			const space = await getDoc<{
				portal_only: number;
				is_published: number;
				root_group: string;
				roles: { role: string; permission_level: string }[];
			}>(request, 'Wiki Space', spaceId);
			expect(space.portal_only).toBe(publicSpace ? 0 : 1);
			expect(space.is_published).toBe(1);
			expect(
				space.roles.map(({ role, permission_level }) => ({
					role,
					permission_level,
				})),
			).toEqual(
				publicSpace ? [{ role: 'Guest', permission_level: 'Read' }] : [],
			);

			// A published page must still be private before a customer mapping or
			// grant exists. Use a fresh anonymous context, never the admin session.
			const marker = `Customer content ${route}`;
			const document = await createDoc<{ name: string; route: string }>(
				request,
				'Wiki Document',
				{
					title: `Page ${route}`,
					content: marker,
					parent_wiki_document: space.root_group,
					is_group: 0,
					is_published: 1,
				},
			);
			const guest = await playwright.request.newContext({
				baseURL,
				storageState: { cookies: [], origins: [] },
			});
			try {
				const reader = await guest.get(`/${document.route}`);
				if (publicSpace) {
					expect(reader.status()).toBe(200);
					expect(await reader.text()).toContain(marker);
				} else {
					expect([403, 404]).toContain(reader.status());
					expect(await reader.text()).not.toContain(marker);
					const resource = await guest.get(
						`/api/resource/Wiki Document/${encodeURIComponent(document.name)}`,
					);
					expect([403, 404]).toContain(resource.status());
					expect(await resource.text()).not.toContain(marker);
				}
			} finally {
				await guest.dispose();
			}

			// Opting into public access must not become the next space's default.
			await page.goto(appUrl('spaces'));
			await page.getByRole('button', { name: 'New Space' }).click();
			await expect(
				page.getByRole('dialog').getByRole('checkbox', {
					name: 'Customer portal only',
				}),
			).toBeChecked();
		},
	);
}
