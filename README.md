<!--
SPDX-FileCopyrightText: 2026 Intevation GmbH <https://intevation.de>
SPDX-License-Identifier: Apache-2.0
-->
# csaf-registry.github.io

## Dependencies
To build the static website you will need
- [hugo](https://gohugo.io)
- [python](https://python.org)
- [pygithub](https://pypi.org/project/PyGithub/)
- [git](https://git-scm.com)

## Building
After cloning the repository, run the following command to pull the submodules:

```sh
git submodule update --init --recursive
```

To download the registry sources run
```sh
./get.py
```

### Development
Finally you can either run the live updating page locally (for development purposes) by running
```sh
hugo serve -D
```
This will also run a web server serving the resulting page on [localhost:1313](https://localhost:1313).

### Production
Or you can generate the HTML files for the purpose of hosting it somewhere by running
```sh
hugo build --minify --baseURL https://example.net
```
The URL needs to be replaced with the domain you intend on hosting the generated HTML from.
