# Southern Flow Plumbing

Static HTML, CSS and JavaScript for [southernflowplumbingllc.com](https://southernflowplumbingllc.com/).
GitHub repository: [PsychoPanda1/southern-flow-plumbing](https://github.com/PsychoPanda1/southern-flow-plumbing).

## Where to work

| File | Purpose |
| --- | --- |
| `site/index.html` | Public copy, photos, contact links, SEO and structured data |
| `site/styles.css` | Branding, responsive layouts, focus styling and error page |
| `site/script.js` | Mobile menu, mobile call links, phone copying and year |
| `site/404.html` | Branded recovery page for missing URLs |
| `site/public/` | Logo, photographs, social preview and icon exports |
| `site/robots.txt`, `site/sitemap.xml`, `site/CNAME` | Crawling and custom domain |
| `scripts/check_site.py` | Dependency-free validation and public packaging |
| `.github/workflows/pages.yml` | Check pull requests; publish successful `main` updates |

The untracked `site/app`, `site/worker`, package files and `.openai` configuration are retained remnants of an unused starter. They are ignored locally. Do not run that starter, edit it as the public website, or create a separate hosting deployment. The local `instagram_archive` retains the original captions, URLs and source photography; `output` holds private owner reports. Neither belongs in the public deployment.

## Preview and check

No npm installation or application server is required for the public website. With Python 3.12+ and Node available:

```sh
python scripts/check_site.py
python -m unittest discover -s tests
node --check site/script.js
python -m http.server 8765 --directory site
```

Open `http://localhost:8765/` for the homepage or `/404.html` for the error-page design. Python's basic server does not automatically serve our custom 404 for missing routes; GitHub Pages does.

To preview precisely the files that will be deployed:

```sh
python scripts/check_site.py --output build/public
python -m http.server 8765 --directory build/public
```

The output directory must be empty. Choose a new folder on subsequent runs if the existing package is still needed. Packaging follows the page's local dependencies, including responsive `srcset` images, CSS references and business/social image metadata. Unreferenced source originals remain in the repository but are not packaged.

## Publish an update

1. Edit the static production files above. Use the established phone number and original media sources.
2. Run the checks and review the page at phone and desktop widths when changing layout. Check the call buttons, menu and keyboard navigation when changing their behavior.
3. Stage only the intended changes. Review `git diff --cached` before committing.
4. Push a branch and open a pull request when review is useful. Pull requests run checks without publishing.
5. Merge or push the approved change to `main`. The Actions workflow validates the site and uploads only the public artifact before deployment.
6. Wait for the `Deploy static site to GitHub Pages` run to finish successfully. Check the live page, contact number and changed assets.

An update to `main` publishes automatically. The README and this workflow do not enforce owner approval; coordinate review with Benjamin/Chase before publishing business claims or changes to customer expectations.

## Domain and search

- Domain registration and DNS: Squarespace.
- Hosting: GitHub Pages using the Actions workflow.
- Primary address: `https://southernflowplumbingllc.com/`.
- HTTPS enforcement was enabled on September 6, 2026. Recheck it after domain or hosting changes.
- Preserve the Search Console verification TXT record when editing DNS. Never commit its value or account credentials.
- Sitemap: `https://southernflowplumbingllc.com/sitemap.xml`. The one-page site needs one canonical entry; an error page should not be listed.
- Change sitemap `lastmod` when the indexed content meaningfully changes, not merely because the deployment ran.

## Maintenance and owner decisions

Benjamin is the recommended technical officer for continued maintenance and development. Owners can also maintain the repository directly or connect their own coding assistant. Repository transfer, account access and future service terms need to reflect the actual agreement; do not describe a transfer as complete until it has occurred.

Before changing the corresponding public claims, obtain owner confirmation of the license number, insurance wording, hours, emergency-service policy, estimate exclusions, primary service area and any additional contact channels. Instagram comments are sourced social feedback; do not manufacture Google reviews, customer identities, star ratings or review schema.

The site currently has no estimate form, analytics integration or application database. No customer submissions are collected by this application. Phone calls and Instagram messages are handled by their respective services. Add tracking, a form, or a new inbox only after its purpose and recipient are agreed.

Keep the local owner PDF and preview image private unless public publication is requested. Domain renewal/payment arrangements belong in the owner handoff, not in the site deployment.

## Recover from an incorrect update

Use Git history to identify the change, then create a reverting commit (`git revert <commit>` for an ordinary non-merge commit) and publish that commit through the same checks. Reverting restores versioned site content; it does not restore DNS, Google settings or untracked files. Avoid rewriting shared history. The original Instagram archive and owner documents should have their own retained copies.

## Browser icons

The compact PNG icons are mechanical size exports of the approved egg emblem. The original stays in `site/public/southern-flow-emblem-badge.png`. To regenerate, run `node scripts/export_icons.cjs` in an environment with `sharp` available. Icon generation is an occasional asset task; Python/Node site checks and hosting do not require `sharp`.
