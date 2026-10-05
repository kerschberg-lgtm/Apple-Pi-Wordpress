# Washington Apple Pi — WordPress evaluation

This repository is a local evaluation copy of the public Washington Apple Pi website, [theapplepi.org](https://www.theapplepi.org). The club is Washington Apple Pi, also called the Pi. Nothing here is deployed or published. The board can use it to look at a possible move from the current site (the pages are served by Weebly) to WordPress.

The wording, menus, and pictures come from the public site. This copy does not add new pages, a new name, or a new logo.

## What is in this repository

| Path | What it is |
| --- | --- |
| `capture/` | The crawl: page HTML, images, the bylaws PDF, `robots.txt`, and `sitemap.xml`. |
| `capture/inventory.json` | The list of pages, blog posts, and media that went into WordPress. |
| `wordpress/wp-content/themes/washington-apple-pi/` | A small classic theme. Page content uses the normal block editor. |
| `wordpress/import/washington-apple-pi.wxr` | A WordPress export (WXR) for any WordPress install, including WordPress.com or a self-hosted host. |
| `wordpress/import/load-local.php` | Loads the WXR into the local preview from the captured files. |
| `wordpress/import/remap-media.php` | After a normal WXR import, points page images at the media library instead of the live site. |
| `docker-compose.yml` and `bin/preview.sh` | Local WordPress and database. One command installs WordPress and loads the content. |
| `scripts/build_wxr.py` | Rebuilds the WXR from `capture/html` if the capture is refreshed. |

## Preview it locally

Docker is required.

```bash
./bin/preview.sh
```

Then open [http://localhost:8080](http://localhost:8080).

The local admin is [http://localhost:8080/wp-admin](http://localhost:8080/wp-admin):

- User: `pi-admin`
- Password: `pi-preview`

Those credentials exist only in this local evaluation copy. The script does not publish the site (search engines are discouraged with `blog_public = 0`).

The first run copies the captured images and the bylaws PDF into the media library. That can take a minute. Later runs reuse the database volume and skip the import. The preview does not need to reach the live site.

To stop it:

```bash
docker compose down
```

`docker compose down -v` also deletes the local database and uploaded media.

### If Docker cannot reach the database by hostname

Some locked-down Docker setups drop traffic between containers. This compose file avoids that by running WordPress in the database container's network and connecting to MySQL at `127.0.0.1`. The site is still published on port 8080.

### Loading the same content somewhere else

1. Install WordPress (6.4 or newer).
2. Upload and activate the theme in `wordpress/wp-content/themes/washington-apple-pi`.
3. Install the WordPress Importer plugin and import `wordpress/import/washington-apple-pi.wxr`. Choose to download attachments. The file's image addresses are the public theapplepi.org URLs, so the importer can fetch them while that site is online.
4. Run `wordpress/import/remap-media.php` with WP-CLI (`wp eval-file wordpress/import/remap-media.php`) so the pages use the copies in the media library. On WordPress.com, a search-and-replace tool can do the same job if the import left images pointing at theapplepi.org.
5. Set Settings → Reading to a static front page (`Home`) and posts page (`Blog`).
6. Assign the **Primary** menu to the Primary location (Appearance → Menus).
7. Set the site logo to the Pi logo (Appearance → Customize, or the logo file in the theme's `assets` folder).
8. Set the permalink structure to "Post name".

## How the current site was mapped

The crawl started at the home page and the sitemap, followed links on theapplepi.org, and skipped anything `robots.txt` disallows. It did not log in, submit forms, or open member-only files on groups.io.

| Live page | WordPress |
| --- | --- |
| Home | Static front page, slug `home` |
| Meet With Us → General Meetings, Clubhouse Saturday, Thursday Learners, Special Interest Groups, RUMP Saturdays | Pages, same menu |
| For Members → Using Join It, Using groups.io, Outreach/Partners, Resist/Reuse/Recycle, Join the Pi, Members only! | Pages, same menu |
| Blog and the nine posts | Posts page plus posts |
| Contact Us | Page. The form fields are reproduced and do not send mail. |
| The Pi Board | Page, including the bylaws PDF in the media library |
| Why Join the Pi, Why Join groups.io, Patience! | Pages linked from Join the Pi, not top-level menu items |
| Using Archives, Volunteer | Pages from the public sitemap. They are not in the visible menu on the live site, so they are not in the WordPress menu either. |
| To-Do | Public checklist page from the sitemap. Not in the menu. The board may want to unpublish it. |

Blog comments that were already public are included. The Pi Day post has two comments. The other posts have comments closed, as they do on the live site.

Menu parents **Meet With Us** and **For Members** are labels, matching the live site (those parent items are not separate pages).

## What did not convert cleanly

- **Contact form.** The fields are on the Contact Us page (name, Pi member, email, comment, devices, where you live). Submitting it does nothing. The live form posts to Weebly and uses reCAPTCHA, which this copy does not call. On WordPress.com, replace it with the Form block. On a self-hosted site, a widely used plugin such as WPForms or Contact Form 7 can email `office@wap.org`.
- **Join It and groups.io.** Membership and discussion stay on those services. The pages link out to them. WordPress is not a replacement for either one unless the board decides to move those jobs later.
- **Members-only material.** The public "Members only!" page is included. It tells members to open presentation files on groups.io. Those files and non-public videos were not copied. Do not put them on a public WordPress page. A future members area could be a password-protected page, a membership plugin, or a link that stays on groups.io.
- **Pages robots.txt tells crawlers to skip.** Not captured: `/the-pi-scholarship.html`, `/newsletter.html`, `/for-members.html`, `/meet-with-us.html`, `/on-social-media.html`, and draft or test pages (`home-draft`, `blog-test`, `test-page`, `site-survey`). The scholarship is still described on the home page and on Outreach/Partners, including the public gift link. The separate scholarship page was left out because of `robots.txt`.
- **YouTube.** General-meeting players are the same YouTube embeds, stored in a Custom HTML block so they play without an extra plugin. A volunteer can swap one for the YouTube block in the editor.
- **Large click-through pictures.** The pictures shown on the pages are in the media library. A few meeting posters also link to a much larger file on the live site (some are over 10 MB). Those large files are kept under `capture/assets/` and are not imported, so the media library stays workable. The on-page picture is the one visitors see.
- **Footer contact link.** The live footer text links to `theapplepi.org/contact.html`, which returns "page not found". The menu item Contact Us is the real page. This copy keeps the footer words and points them at Contact Us.
- **Search.** The current header has no search box, so this theme does not add one. WordPress search is available if the board wants it later.
- **Social icons.** Facebook, YouTube, Twitter (`twitter.com/Pi_org`), and email (`office@wap.org`) are text links in the footer instead of the Weebly icon font.
- **Weebly membership login.** There is no member login on this copy. The live members area is groups.io.
- **Older site.** Links to wap.org are left as links. That site was not copied.
- **Email addresses.** The live pages hide addresses with Cloudflare's email protection. This copy uses the public addresses those scripts reveal: `office@wap.org` and `president@wap.org`.

Volunteers edit pages and posts in the block editor (Pages and Posts). The menu is under Appearance → Menus. The theme is ordinary PHP for the header, footer, and blog list. It does not add a custom post type or a page builder.

## Migration options

The figure of about **$150 to $250 a year** is a reasonable budget for a small self-hosted WordPress site: a modest shared or managed WordPress plan, plus the domain if it is not already paid for. It is a hosting budget, not a fee for an AI add-on.

**Self-hosted WordPress** (a typical club choice at that budget):

1. Pick a host that offers one-click WordPress. Keep a backup option.
2. Install WordPress and import this WXR and theme, using the steps above.
3. Replace the contact form so mail goes to the club.
4. Leave Join It and groups.io in place. The site already links to them.
5. Point the domain's DNS at the new host when the board is ready. Until then, the current Weebly site can stay up.
6. Ask the host about automatic updates, backups, and HTTPS.

**WordPress.com**:

- Importing the WXR works on WordPress.com.
- Installing this theme, or a form plugin, needs a plan that allows plugins and custom themes (the Business plan, under current WordPress.com packaging). That plan is often above a $150–$250 yearly budget. Check the prices on WordPress.com before choosing it.
- A lower WordPress.com plan can hold the pages if the board is willing to restyle them in the WordPress.com editor instead of using this theme.

**AI-assisted updates and MCP.** WordPress core does not ship an MCP server. A self-hosted site can add the [WordPress MCP Adapter](https://github.com/WordPress/mcp-adapter) (the WordPress AI team's plugin) or a similar plugin so an assistant can draft updates through WordPress's own APIs. Plugin installs on WordPress.com depend on the plan. People can also keep editing in wp-admin with no AI connection. Several volunteers can share the Editor or Administrator role; that is the maintenance path this copy is built for.

## Rebuilding the import file

After a new crawl into `capture/html`:

```bash
python3 scripts/build_wxr.py
```

That rewrites `wordpress/import/washington-apple-pi.wxr` and `capture/inventory.json`.
