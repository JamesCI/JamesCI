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


## Concept

After each commit, James CI will extract the configuration from a file stored in
the repository just like other CI's do, too. The extracted script will be
executed, or passed to an external handler, e.g. if you need parallel execution,
or want to use a scheduler like [SLURM](https://slurm.schedmd.com).

All required data is stored in flat-files which will be evaluated by a simple UI
written in PHP using the [Silex](https://github.com/silexphp/Silex)
microframework and the [Twig](https://github.com/twigphp/Twig) template engine,
so it's easy to install and customize.

All in all James CI tries to be as simple as possible. Any specialization for
the local environment should take place in helper scripts and is not part of the
CI itself.


## Configuring Your Project

Using James CI should be as simple as using other CI's. Therefore a YAML file
named `.james-ci.yml` stored in your repository will be used for configuring the
jobs. Its structure is similar (but not equal) to the one known by
[Travis CI](http://travis-ci.org/).

A simple configuration file might look like this:

```YAML
jobs:
  sample:
    script:
      - mkdir build && cd build
      - cmake ..
      - make all test install
```

### The Job Lifecycle

Each job is made up of three steps:

* `install`: Install dependencies required for your build job.
* `script`: Run the build script.
* `deploy`: Deploying build artifacts.

Additional commands may be run before the `install` step (`before_install`),
before (`before_script`) and after (`after_script`) the  `script` step.
Depending on if the `script` step succeeds or not, either `after_success` or
`after_failure` will be run. If the `script` step succeeds, the three additional
steps `before_deploy`, `deploy` and `after_deploy` will be run.

Each step may be defined global for all job steps, or individually for each job.
Empty steps will be skipped. E.g. for the following config, one job would print
`a` and the other `b` in the job's log:

```YAML
jobs:
  job_a:
  job_b: echo 'b'

script: echo 'a'
```

The complete job lifecycle, after checking out the git repository and changing
into the repositories directory, is:

1. `before_install`
2. `install`
3. `before_script`
4. `script`
5. `after_success` or `after_failure`
6. `before_deploy`
7. `deploy`
8. `after_deploy`
9. `after_script`

### Breaking the Job

If any of the commands in any step of the jobs lifecycle fails, no further
commands will be executed (see exceptions in `script` step below). The status of
the job depends on the step that failed:

* If `before_install`, `install`, `before_script` or `before_deploy` return a
  non-zero exit code, the job's status will be *errored*.
* If `script` or `deploy` return a non-zero exit code, the job is failed. For
  `script` `after_failure` will be executed before leaving the job.
* If `after_success`, `after_failure`, `after_deploy` or `after_script` return a
  non-zero exit code, this doesn't affect the job's status.
