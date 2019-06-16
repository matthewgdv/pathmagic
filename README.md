Overview
====================

Provides a Maybe class which can be used to avoid common 'var if var is not None else handle_none(var)' structures.
Maybe allows item access, attribute access, and method calls to be chained off it. It can be combined with most operators.

Installation
====================

To install use pip:

    $ pip install maybe


Or clone the repo:

    $ git clone https://github.com/matthewgdv/maybe.git
    $ python setup.py install


Usage
====================

The simplest use-case is to Wrap the value in the Maybe class and call Maybe.else_() with an alternative value. If the initial value
was None, the alternative value will be returned. Otherwise the original value will be returned.

    Maybe(None).else_("other")                      # "other"
    Maybe("hi").else_("other")                      # "hi"

More complex uses involve chaining item/attribute access and method calls off the initial value.
If at any point an IndexError (item access), AttributeError (attribute access), or TypeError (method call) is raised, the alternative
value will be returned. Other exception classes are not caught by Maybe (intentionally) and will have be to handled normally.

    Maybe("hi").monkeyweasel[3].else_("other")      # "other"
    Maybe({1: "1"})[1].isnumeric().else_("other")   # True

Most operators can be used with Maybe.

    (Maybe(8)/2).else_("other")                     # 4.0
    (Maybe("hi").upper() + "!").else_("other")      # "HI!"
    (Maybe(None) // 3).else_("other")               # "other"
    (Maybe(11) % 4).else_("other")                  # 3

If None would be retuned as a result of operations performed on the Maybe object, then None will be returned from Maybe.else_(), not
the alternative value. This is because None is a legitimate output value, so long as it was not the original input value.

    Maybe({1: "1"}).get(2).else_("other")           # None

The Maybe class will show the repr of the object it currently contains in its own repr (if it would return the alternative value from Maybe.else_() it will show it as MissingValue).
Additionally, the Maybe class will be truthy whenever it would return what it is currently holding, and will be falsy when it would return the alternative.

Contributing
====================

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Report Bugs
--------------------

Report bugs at https://github.com/matthewgdv/maybe/issues

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
--------------------

Look through the GitHub issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement a fix for it.

Implement Features
--------------------

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
--------------------

The repository could always use more documentation, whether as part of the
official docs, in docstrings, or even on the web in blog posts, articles, and such.

Submit Feedback
--------------------

The best way to send feedback is to file an issue at https://github.com/matthewgdv/maybe/issues.

If you are proposing a new feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions are welcome :)

Get Started!
--------------------

Before you submit a pull request, check that it meets these guidelines:

1.  The pull request should include tests.

2.  If the pull request adds functionality, the docs should be updated. Put
    your new functionality into a function with a docstring, and add the
    feature to the list in README.md.

3.  The pull request should work for Python 3.7. Older versions are not supported.

4.  PEP8 guidelines should be followed where possible, but deviations from it where
    it makes sense and improves legibility are encouraged. Do not be dogmatic.

5.  This repository intentionally disallows the PEP8 79-character limit. Therefore,
    any contributions adhering to this convention will be rejected. As a rule of
    thumb you should endeavor to stay under 200 characters except where going over
    preserves alignment, or where the line is mostly non-algorythmic code, such as
    an extremely long descriptive string or function call.
