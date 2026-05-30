FROM alpine:latest

# Install LLDP daemon and OpenSSH server (to allow the agent to connect if needed)
RUN apk update && \
    apk add --no-cache lldpd openssh iproute2 tcpdump

# Configure SSH
RUN ssh-keygen -A && \
    echo 'root:root' | chpasswd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
