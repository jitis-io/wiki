import { expect, test } from '../fixtures';
import { getDoc } from '../helpers/frappe';

const publicHelp = 'Make this wiki space publicly accessible';
const portalHelp =
	'Published pages are available to authorized portal customers. This space is not publicly accessible.';
const publicAccessHelp =
	'Readable by all logged-in users if no roles are set. Add the Guest role for public/anonymous access.';
const portalAccessHelp =
	'Customer portal access is controlled by portal access grants. Wiki roles, including Guest, do not grant customer access.';

for (const scenario of [
	{ name: 'ordinary space', portalOnly: 0, roles: [] },
	{ name: 'portal space without Wiki roles', portalOnly: 1, roles: [] },
	{
		name: 'portal space with a legacy Guest role',
		portalOnly: 1,
		roles: [{ role: 'Guest', permission_level: 'Read' }],
	},
]) {
	test(`settings explain access for ${scenario.name}`, async ({
		page,
		request,
		wiki,
	}) => {
		const space = await wiki.space({
			portal_only: scenario.portalOnly,
			is_published: true,
			roles: scenario.roles,
		});

		await page.setViewportSize({ width: 1280, height: 900 });
		await page.goto(space.url());
		await page.getByRole('button', { name: 'Space actions' }).click();
		await page.getByRole('menuitem', { name: 'Space settings' }).click();
		const dialog = page.getByRole('dialog');
		await expect(dialog).toBeVisible();

		await expect(
			dialog.getByText(scenario.portalOnly ? portalHelp : publicHelp, {
				exact: true,
			}),
		).toBeVisible();
		await expect(
			dialog.getByText(scenario.portalOnly ? publicHelp : portalHelp, {
				exact: true,
			}),
		).toHaveCount(0);

		// The explanation must not introduce a second publication state or
		// accidentally change the server-enforced portal protection.
		const publishSwitch = dialog.getByRole('switch');
		await publishSwitch.click();
		await expect
			.poll(async () => {
				const doc = await getDoc<{
					is_published: number;
					portal_only: number;
				}>(request, 'Wiki Space', space.name);
				return [doc.is_published, doc.portal_only];
			})
			.toEqual([0, scenario.portalOnly]);

		await dialog.getByRole('tab', { name: 'Access', exact: true }).click();
		await expect(
			dialog.getByText(
				scenario.portalOnly ? portalAccessHelp : publicAccessHelp,
				{ exact: true },
			),
		).toBeVisible();
		await expect(
			dialog.getByText(
				scenario.portalOnly ? publicAccessHelp : portalAccessHelp,
				{ exact: true },
			),
		).toHaveCount(0);
		if (!scenario.roles.length) {
			await expect(
				dialog.getByText(
					scenario.portalOnly
						? 'No Wiki roles configured. Customer access is controlled by portal access grants.'
						: 'No roles configured (open to all logged-in users).',
					{ exact: true },
				),
			).toBeVisible();
		} else {
			await expect(
				dialog.getByRole('cell', { name: 'Guest', exact: true }),
			).toBeVisible();
		}
	});
}
