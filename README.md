# James CI

[![](http://img.shields.io/badge/license-GPL-blue.svg?style=flat-square)](LICENSE)

Simple CI server for small projects.


## About

Continuous integration and delivery are pretty nice features, but several
implementations have a common disadvantage: Most CI software is designed for up
to large environments, including all the overhead and large-scale solutions. But
most CI jobs for private projects or small integrations do require only a subset
of the provided features.

For most projects in these environments a git server-side post-commit hook would
just work fine, but these are not very flexible to use. In addition these would
have to be configured for every single repository. But why not combine several
systems to get the flexibility of professional CI in small scale?

James just provides the really basic infrastructure for your CI server to have a
tiny footprint and be very flexible to use. It aims to be the CI pendant of
[GitList](http://gitlist.org): By default there is no authentication, just a
small amount of configuration and no special features.


### Concept

After each commit, James CI will extract the configuration from a file stored in
the repository just like other CI's do, too. The extracted script will be
executed, or passed to an external script if you need e.g. parallel execution,
or want to use a scheduler like [SLURM](https://slurm.schedmd.com).

All required data is stored in flat-files which will be evaluated by a simple UI
written in PHP using the [Silex](https://github.com/silexphp/Silex)
microframework and the [Twig](https://github.com/twigphp/Twig) template engine,
so it's easy to install and customize.

All in all James CI tries to be as simple as possible. Any specialization for
the local environment should take place in helper scripts and is not part of the
CI itself.
