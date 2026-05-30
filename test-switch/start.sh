#!/bin/sh

# Start LLDP daemon
# -d: run in foreground, but we'll background it to run sshd too.
# However, for Docker we usually want a foreground process. We'll background lldpd and foreground sshd.
/usr/sbin/lldpd

# Start SSH daemon in foreground so container stays alive
/usr/sbin/sshd -D
