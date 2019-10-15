# [Doodba](https://hub.docker.com/r/tecnativa/doodba)

[![](https://images.microbadger.com/badges/version/tecnativa/doodba:latest.svg)](https://microbadger.com/images/tecnativa/doodba:latest "Get your own version badge on microbadger.com")
[![](https://images.microbadger.com/badges/image/tecnativa/doodba:latest.svg)](https://microbadger.com/images/tecnativa/doodba:latest "Get your own image badge on microbadger.com")
[![](https://images.microbadger.com/badges/commit/tecnativa/doodba:latest.svg)](https://microbadger.com/images/tecnativa/doodba:latest "Get your own commit badge on microbadger.com")
[![](https://images.microbadger.com/badges/license/tecnativa/doodba.svg)](https://microbadger.com/images/tecnativa/doodba "Get your own license badge on microbadger.com")

[![](https://api.travis-ci.org/Tecnativa/doodba.svg)](https://travis-ci.org/Tecnativa/doodba)

Install [Odoo](https://www.odoo.com) **Ba**se with **Doodba** library and scripts.

## Directories tree

Basically, every directory you have to worry about is found inside `$HOME/odoo`.
This is its structure:

    custom/
        entrypoint.d/
        build.d/
        conf.d/
        dependencies/
            apt_build.txt
            apt.txt
            gem.txt
            npm.txt
            pip.txt
        src/
            private/
            odoo/
            addons.yaml
            repos.yaml
    common/
        entrypoint
        build
        entrypoint.d/
        build.d/
        conf.d/
    auto
        addons/
        odoo.conf

Let's go one by one.

### `$HOME/odoo/custom`: The important one

Here you will put everything related to your project.

#### `$HOME/odoo/custom/entrypoint.d`

Any executables found here will be run when you launch your container, before
running the command you ask.

#### `$HOME/odoo/custom/build.d`

Executables here will be aggregated with those in `$HOME/odoo/common/build.d`.

The resulting set of executables will then be sorted alphabetically (ascending)
and then subsequently run.

#### `$HOME/odoo/custom/conf.d`

Files here will be environment-variable-expanded and concatenated in
`$HOME/odoo/auto/odoo.conf` in the entrypoint.

#### `$HOME/odoo/custom/src`

Here you will put the actual source code for your project.

When putting code here, you can either:

- Use [`repos.yaml`][], that will fill anything at build time.
- Directly copy all there.

Recommendation: use [`repos.yaml`][] for everything except for [`private`][],
and ignore in your `.gitignore` and `.dockerignore` files every folder here
except [`private`][], with rules like these:

    odoo/custom/src/*
    !odoo/custom/src/private
    !odoo/custom/src/*.*

##### `$HOME/odoo/custom/src/odoo`

**REQUIRED.** The source code for your odoo project.

You can choose your Odoo version, and even merge PRs from many of them using
[`repos.yaml`][]. Some versions you might consider:

- [Original Odoo][], by [Odoo S.A.][].

- [OCB][] (Odoo Community Backports), by [OCA][].
  The original + some features - some stability strictness.

- [OpenUpgrade][], by [OCA][].
  The original, frozen at new version launch time + migration scripts.

##### `$HOME/odoo/custom/src/private`

**REQUIRED.** Folder with private addons for the project.

##### `$HOME/odoo/custom/src/repos.yaml`

A [git-aggregator](#git-aggregator) configuration file.

It should look similar to this:

```yaml
# Odoo must be in the `odoo` folder for Doodba to work
odoo:
  defaults:
    # This will use git shallow clones.
    # $DEPTH_DEFAULT is 1 in test and prod, but 100 in devel.
    # $DEPTH_MERGE is always 100.
    # You can use any integer value, OTOH.
    depth: $DEPTH_MERGE
  remotes:
    origin: https://github.com/OCA/OCB.git
    odoo: https://github.com/odoo/odoo.git
    openupgrade: https://github.com/OCA/OpenUpgrade.git
  # $ODOO_VERSION is... the Odoo version! "11.0" or similar
  target: origin $ODOO_VERSION
  merges:
    - origin $ODOO_VERSION
    - odoo refs/pull/25594/head # Expose `Field` from search_filters.js

web:
  defaults:
    depth: $DEPTH_MERGE
  remotes:
    origin: https://github.com/OCA/web.git
    tecnativa: https://github.com/Tecnativa/partner-contact.git
  target: origin $ODOO_VERSION
  merges:
    - origin $ODOO_VERSION
    - origin refs/pull/1007/head # web_responsive search
    - tecnativa 11.0-some_addon-custom # Branch for this customer only
```

###### Automatic download of repos

Doodba is smart enough to download automatically git repositories even if they
are missing in `repos.yaml`. It will happen if it is used in [`addons.yaml`][],
except for the special [`private`][] repo. This will help you keep your
deployment definitions DRY.

You can configure this behavior with these environment variables (default
values shown):

- `DEFAULT_REPO_PATTERN="https://github.com/OCA/{}.git"`
- `DEFAULT_REPO_PATTERN_ODOO="https://github.com/OCA/OCB.git"`

As you probably guessed, we use something like `str.format(repo_basename)`
on top of those variables to compute the default remote origin. If, i.e.,
you want to use your own repositories as default remotes, just change these lines in your `$HOME/.bashrc` file to be:

```bash
export DEFAULT_REPO_PATTERN_ODOO="https://github.com/Tecnativa/{}.git"
export DEPTH_DEFAULT="*origin"
```

So, for example, if your [`repos.yaml`][] file is empty and
your [`addons.yaml`][] contains this:

```yaml
server-tools:
- module_auto_update
```

A `$HOME/odoo/auto/repos.yaml` file with this will be generated and used to
download git code:

```yaml
$HOME/odoo/custom/src/odoo:
  depth: $DEPTH_DEFAULT
  remotes:
    origin: https://github.com/OCA/OCB.git
  target: origin $ODOO_VERSION
  merges:
    - origin $ODOO_VERSION
$HOME/odoo/custom/src/server-tools:
  depth: $DEPTH_DEFAULT
  remotes:
    origin: https://github.com/OCA/server-tools.git
  target: origin $ODOO_VERSION
  merges:
    - origin $ODOO_VERSION
```

All of this means that, you only need to define the git aggregator
spec in [`repos.yaml`][] if anything diverges from the standard:

- You need special merges.
- You need a special origin.
- The folder name does not match the origin pattern.
- The branch name does not match `$ODOO_VERSION`.
- Etc.

##### `$HOME/odoo/custom/src/addons.yaml`

One entry per repo and addon you want to activate in your project. Like this:

```yaml
website:
    - website_cookie_notice
    - website_legal_page
web:
    - web_responsive
```

Advanced features:

- You can bundle [several YAML documents][] if you want to logically group your
  addons and some repos are repeated among groups, by separating each document
  with `---`.

- Addons under `private` and `odoo/addons` are linked automatically unless you
  specify them.

- You can use `ONLY` to supply a dictionary of environment variables and a
  list of possible values to enable that document in the matching environments.

- If an addon is found in several places at the same time, it will get linked
  according to this priority table:

  1. Addons in [`private`][].
  2. Addons in other repositories (in case one is matched in several, it will
     be random, BEWARE!). Better have no duplicated names if possible.
  3. Core Odoo addons from [`odoo/addons`][`odoo`].

- If an addon is specified but not available at runtime, it will fail silently.

- You can use any wildcards supported by [Python's glob module][glob].

This example shows these advanced features:

```yaml
# Spanish Localization
l10n-spain:
  - l10n_es # Overrides built-in l10n_es under odoo/addons
server-tools:
  - "*date*" # All modules that contain "date" in their name
  - module_auto_update # Makes `autoupdate` script actually autoupdate addons
web:
  - "*" # All web addons
---
# Different YAML document to separate SEO Tools
website:
  - website_blog_excertp_img
server-tools: # Here we repeat server-tools, but no problem because it's a
              # different document
  - html_image_url_extractor
  - html_text
---
# Enable demo ribbon only for devel and test environments
ONLY:
  PGDATABASE: # This environment variable must exist and be in the list
    - devel
    - test
web:
  - web_environment_ribbon
---
# Enable special authentication methods only in production environment
ONLY:
  PGDATABASE:
    - prod
server-tools:
  - auth_*
```

##### `$HOME/odoo/custom/dependencies/*.txt`

Files to indicate dependencies of your subimage, one for each of the supported
package managers:

- `gem.txt`: run-time dependencies installed by gem.
- `npm.txt`: run-time dependencies installed by npm.
- `pip.txt`: a normal [pip `requirements.txt`][] file, for run-time
  dependencies too. It will get executed with `--update` flag, just in case
  you want to overwrite any of the pre-bundled dependencies.

### `$HOME/odoo/common`: The useful one

This folder is full of magic. I'll document it some day. For now, just look at
the code.

Only some notes:

- Will compile your code with [`PYTHONOPTIMIZE=1`][] by default.

- Will remove all code not used from the image by default (not listed in
  `$HOME/odoo/custom/src/addons.yaml`), to keep it thin.

### `$HOME/odoo/auto`: The automatic one

This directory will have things that are automatically generated at build time.

#### `$HOME/odoo/auto/addons`

It will be full of symlinks to the addons you selected in [`addons.yaml`][].

#### `$HOME/odoo/auto/odoo.conf`

It will have the result of merging all configurations under
`$HOME/odoo/{common,custom}/conf.d/`, in that order.

## Bundled tools

There is a good collections of tools available in the image that help dealing
with Odoo and its peculiarities:

### `addons`

A handy CLI tool to automate addon management based on the current environment.
It allows you to install, update, test and/or list private, extra and/or core
addons available to current container, based on current [`addons.yaml`][]
configuration.

Call `addons --help` for usage instructions.

### `click-odoo` and related scripts

The great [`click-odoo`][] scripting framework and the collection of scripts
found in [`click-odoo-contrib`][] are included. Refer to their sites to know
how to use them.

### `log`

Just a little shell script that you can use to add logs to your build or
entrypoint scripts:

    log INFO I'm informing

### `pot`

Little shell shortcut for exporting a translation template from any addon(s).
Usage:

    pot my_addon,my_other_addon

### `python-odoo-shell`

Little shortcut to make your `odoo shell` scripts executable.

For example, create this file in your scaffolding-based project:
`$HOME/odoo/whoami.py`. Fill it with:

```python
#!/usr/local/bin/python-odoo-shell
from __future__ import print_function
print(env.user.name)
print(env.context)
```

Now run it:

```bash
$ chmod a+x $HOME/odoo/whoami.py  # Make it executable
$ $HOME/odoo/whoami.py
```

### `unittest`

Another little shell script, useful for debugging. Just run it like this and
Odoo will execute unit tests in its default database:

    unittest my_addon,my_other_addon

Note that the addon must be installed for it to work. Otherwise, you should run
it as:

    unittest my_addon,my_other_addon -i my_addon,my_other_addon

### [`ptvsd`](https://github.com/DonJayamanne/pythonVSCode)

[VSCode][] debugger. If you use this editor with its python module, you will
find it useful.

To debug at a certain point of the code, add this Python code somewhere:

```python
import ptvsd
ptvsd.enable_attach("doodba-rocks", address=("0.0.0.0", 6899))
print("ptvsd waiting...")
ptvsd.wait_for_attach()
```

To start Odoo within a ptvsd environment, which will obey the breakpoints
established in your IDE (but will work slowly), just add `-e PTVSD_ENABLE=1`
to your odoo container.

Of course, you need to have properly configured your [VSCode][]. To do so, make
sure in your project there is a `.vscode/launch.json` file with these minimal
contents:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Attach to debug in devel.yaml",
            "type": "python",
            "request": "attach",
            "pathMappings": [
                {
                    "localRoot": "${workspaceRoot}/odoo",
                    "remoteRoot": "$HOME/odoo"
                }
            ],
            "port": 6899,
            "host": "localhost"
        }
    ]
}
```

Then, execute that configuration as usual.

### [`pudb`](https://github.com/inducer/pudb)

This is another great debugger that includes remote debugging via telnet, which
can be useful for some cases, or for people that prefer it over [wdb](#wdb).

To use it, inject this in any Python script:

```python
import pudb.remote
pudb.remote.set_trace(term_size=(80, 24))
```

Then open a telnet connection to it:

    telnet CONTAINER_IP 6899

**IN PRODUCTION ENVIRONMENTS.** use ssh proxy to forward `CONTAINER_IP:6899` to your local.

### [`git-aggregator`](https://pypi.python.org/pypi/git-aggregator)

We found this one to be the most useful tool for downlading code, merging it
and placing it somewhere.

### `autoaggregate`

This little script wraps `git-aggregator`.

#### Example [`repos.yaml`][] file

This example merges [several sources][`odoo`]:

```yaml
./odoo:
    defaults:
        # Shallow repositores are faster & thinner. You better use
        # $DEPTH_DEFAULT here when you need no merges.
        depth: $DEPTH_MERGE
    remotes:
        ocb: https://github.com/OCA/OCB.git
        odoo: https://github.com/odoo/odoo.git
    target:
        ocb $ODOO_VERSION
    merges:
        - ocb $ODOO_VERSION
        - odoo refs/pull/13635/head
```

### [`odoo`](https://www.odoo.com/documentation/10.0/reference/cmdline.html)

We set an `$OPENERP_SERVER` environment variable pointing to [the autogenerated
configuration file](#optodooautoodooconf) so you don't have to worry about
it. Just execute `odoo` and it will work fine.

Note that version 9.0 has an `odoo` binary to provide forward compatibility
(but it has the `odoo.py` one too).

### Skip the boring parts

You will need these tool, check their docs:

- [Git](https://git-scm.com/do)

###### [`wdb`](https://github.com/Kozea/wdb/)

This is one of the greatest Python debugger available, and even more for
Docker-based development, so here you have it preinstalled.

I told you, this image is opinionated. :wink:

To use it, write this in any Python script:

```python
import wdb
wdb.set_trace()
```

It's available by default on the development environment,
where you can browse http://CONTAINER_IP:1984 to use it.

**IN PRODUCTION ENVIRONMENTS.** use ssh proxy to forward `CONTAINER_IP:1984` to your local.

###### [MailHog](https://github.com/mailhog/MailHog)

It provides a fake SMTP server that intercepts all mail sent by Odoo and
displays a simple interface that lets you see and debug all that mail
comfortably, including headers sent, attachments, etc.

- For development, it's in http://localhost:8025
- For testing, it's in http://$DOMAIN_TEST/smtpfake/
- For production, use ssh proxy to forward `CONTAINER_IP:8025` to your local

All environments are configured by default to use the bundled SMTP relay.
They are configured by these environment variables:

- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_SSL`
- `EMAIL_FROM`

For them to be useful, you need to remove any `ir.mail_server` records in your
database.

##### Run unit tests for some addon

    odoo --stop-after-init --init addon1,addon2
    unittest addon1,addon2

##### Install some addon without stopping current running process

    odoo -i addon1,addon2 --stop-after-init

##### Update some addon without stopping current running process

    odoo -u addon1,addon2 --stop-after-init

##### Update changed addons only

Add `module_auto_update` from https://github.com/OCA/server-tools to your
installation following the standard methods of `repos.yaml` + `addons.yaml`.

Now we will install the addon:

     odoo --stop-after-init -u base
    odoo --stop-after-init -i module_auto_update
    odoo-restart

It will automatically update addons that got updated every night.
To force that automatic update now:

    odoo autoupdate
    odoo-restart

##### Export some addon's translations to stdout

    odoo pot addon1[,addon2]

Now copy the relevant parts to your `addon1.pot` file.

##### Open an odoo shell

    odoo shell

### How to have good QA and test in my CI with Doodba?

we have `$HOME/qa` folder, which provides some necessary
plumbing to perform quality assurance and continous integration if you use
[doodba-qa][], which is a separate (but related) project with that purpose.

Go there to get more instructions.

[`$HOME/odoo/auto/addons`]: #optodooautoaddons
[`addons.yaml`]: #optodoocustomsrcaddonstxt
[`odoo.conf`]: #optodooautoodooconf
[`odoo`]: #optodoocustomsrcodoo
[`private`]: #optodoocustomsrcprivate
[`PYTHONOPTIMIZE=1`]: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONOPTIMIZE
[`repos.yaml`]: #optodoocustomsrcreposyaml
[`click-odoo`]: https://github.com/acsone/click-odoo
[`click-odoo-contrib`]: https://github.com/acsone/click-odoo-contrib
[doodba-qa]: https://github.com/Tecnativa/doodba-qa
[glob]: https://docs.python.org/3/library/glob.html
[MailHog]: #mailhog
[OCA]: https://odoo-community.org/
[OCB]: https://github.com/OCA/OCB
[Odoo S.A.]: https://www.odoo.com
[OpenUpgrade]: https://github.com/OCA/OpenUpgrade/
[Original Odoo]: https://github.com/odoo/odoo
[pip `requirements.txt`]: https://pip.readthedocs.io/en/latest/user_guide/#requirements-files
[several YAML documents]: http://www.yaml.org/spec/1.2/spec.html#id2760395
[VSCode]: https://code.visualstudio.com/
