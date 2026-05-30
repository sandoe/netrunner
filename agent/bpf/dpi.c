//go:build ignore

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

struct event {
    __u32 saddr;
    __u32 daddr;
    __u16 sport;
    __u16 dport;
    __u32 rule_id; // Matched rule ID
};

// Force BTF emission for struct event
struct event *unused_event __attribute__((unused));

// Define a BPF ring buffer to send events to userspace
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

#define MAX_RULES 32

struct rule {
    __u32 rule_id;
    __u16 dport; // 0 means any port
    __u16 sig_len; // max 8
    __u8 signature[8];
};

struct rule *unused_rule __attribute__((unused));

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __type(key, __u32);
    __type(value, struct rule);
    __uint(max_entries, MAX_RULES);
} rules_map SEC(".maps");

SEC("socket")
int socket_dpi(struct __sk_buff *skb) {
    if (skb->protocol != bpf_htons(ETH_P_IP))
        return 0;

    struct iphdr iph;
    if (bpf_skb_load_bytes(skb, ETH_HLEN, &iph, sizeof(iph)) < 0)
        return 0;

    if (iph.protocol != IPPROTO_TCP)
        return 0;

    struct tcphdr tcph;
    int tcp_offset = ETH_HLEN + (iph.ihl * 4);
    if (bpf_skb_load_bytes(skb, tcp_offset, &tcph, sizeof(tcph)) < 0)
        return 0;

    int payload_offset = tcp_offset + (tcph.doff * 4);
    
    // Load up to 8 bytes of payload
    __u8 payload[8] = {0};
    if (bpf_skb_load_bytes(skb, payload_offset, payload, sizeof(payload)) < 0) {
        // We might just have a smaller payload, let's load what we can
        // For simplicity, if we can't load 8 bytes, we just try to read byte by byte or ignore.
        // Actually, if it's smaller, load_bytes fails. Let's just ignore packets < 8 bytes payload for now.
        // Or we could read it carefully. Let's stick to 8 bytes.
        return 0;
    }
        
    #pragma unroll
    for (int i = 0; i < MAX_RULES; i++) {
        __u32 key = i;
        struct rule *r = bpf_map_lookup_elem(&rules_map, &key);
        if (!r) continue;
        if (r->rule_id == 0) continue; // empty slot

        // Check port
        if (r->dport != 0 && r->dport != bpf_ntohs(tcph.dest))
            continue;

        // Check signature
        if (r->sig_len > 0 && r->sig_len <= 8) {
            int match = 1;
            for (int j = 0; j < 8; j++) {
                if (j >= r->sig_len) break;
                if (payload[j] != r->signature[j]) {
                    match = 0;
                    break;
                }
            }
            
            if (match) {
                struct event *e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
                if (e) {
                    e->saddr = iph.saddr;
                    e->daddr = iph.daddr;
                    e->sport = tcph.source;
                    e->dport = tcph.dest;
                    e->rule_id = r->rule_id;
                    bpf_ringbuf_submit(e, 0);
                }
                break; // Stop evaluating after first rule match
            }
        }
    }

    return 0;
}

char _license[] SEC("license") = "GPL";
