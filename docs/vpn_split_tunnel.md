# CookBot VPN Split Tunnel

Manual CookBot control must work without internet and without VPN.

If an OpenAI-compatible API is used later, route only outbound AI API traffic through VPN. Keep local phone-to-UNO-Q traffic on the LAN.

Default MVP behavior:

- backend binds to `127.0.0.1`;
- LAN exposure must be explicit;
- no public internet robot control;
- no cloud backend dependency.

Example WireGuard starting file:

```text
deploy/wireguard/cookbot-ai-split-tunnel.example.conf
```

That file is not complete policy routing. Before enabling it, restrict routing to AI API traffic and confirm the phone can still reach the UNO Q local address directly.
