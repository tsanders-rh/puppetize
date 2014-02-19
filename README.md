puppetize
=========

Prototype Tool for converting Spacewalk Configuration Channel into a self-contained Puppet Module

To run:

1. Update /etc/puppetize/puppetize.conf to include proper API credentials for Spacewalk Server.
2. python puppetize.py -c <config-channel>.
3. Module built in /tmp by default.
4. puppet module build
5.
