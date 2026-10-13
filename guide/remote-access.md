# Phone, own domain and other PCs

## Use Venus on your phone

[Tailscale](https://tailscale.com) is a free private network between your
own devices. Only devices signed in to your Tailscale account can open
Venus, nothing is on the public internet. You get HTTPS, so the phone's mic
works too.

1. Install Tailscale on the PC and the phone, same account.
2. In the Tailscale admin console, DNS page: turn on MagicDNS and HTTPS
   Certificates.
3. With Venus running:

```powershell
.\scripts\phone-access.ps1          # Windows
```

```bash
./scripts/phone-access.sh           # Linux
```

It prints something like `https://my-pc.tailnet-name.ts.net`. Open that on
your phone with Tailscale connected and log in. It stays on after a reboot.
`-Off` (Windows) or `--off` (Linux) stops it.

On Linux, if `tailscale serve` says access denied, run
`sudo tailscale set --operator=$USER` once.

## Your own domain (optional)

Instead of the `ts.net` name you can use a domain you own, like
`https://venus.example.com`. Still private: the domain points at the PC's
Tailscale address, which only your devices can reach.
[Caddy](https://caddyserver.com) answers there (about 45 MB of RAM) and gets
a free certificate through your DNS. These steps assume your DNS is on
Cloudflare.

1. Set up Tailscale as above. `tailscale ip -4` shows the PC's address
   (starts with `100.`).
2. In Cloudflare add an `A` record (for example `venus`) to that address,
   proxy off ("DNS only", grey cloud).
3. Make a Cloudflare API token with the "Edit zone DNS" template, only for
   that domain.
4. In the root `.env` set `VENUS_DOMAIN=venus.example.com` and
   `CLOUDFLARE_API_TOKEN=...`.
5. Run `.\scripts\domain-access.ps1` (Windows) or
   `./scripts/domain-access.sh` (Linux).

It downloads Caddy into `tools/caddy` (asks first), stops the `ts.net` share
and restarts the tray app, which keeps Caddy running from then on. Caddy's
log is `apps/node/data/caddy.log`. To go back: empty `VENUS_DOMAIN`, restart
Venus, run phone-access again.

## Another PC

A second PC (a laptop, say) can run just the Node and take commands from
the same Venus. It reaches Core over Tailscale.

1. On the main PC, set up phone access or your own domain (above). Both
   print the address for other PCs, like
   `wss://venus.example.com:9443/nodes/connect`.
2. On the main PC: Settings, Devices, Add device. Copy the token (it's only
   shown once).
3. On the other PC: install Tailscale (same account) and Python 3.11+, clone
   Venus and run `setup-venus-node.cmd` (Windows) or
   `./setup-venus.sh --node-only` (Linux). Give it the address and the token.
   No Docker needed there.

Once two PCs are online the chat shows a PC picker next to the send button.
"Hey Venus" only runs on the main PC for now.

## Devices and logins

Settings, Devices shows every PC with its own token and when it was last
seen. Revoke cuts one off right away.

- The main PC's token (from setup) shows up as "Main PC". It can't be revoked
  from the web, so someone with a stolen phone login can't lock you out of
  your own PC. To change it, edit it in both `apps/core/.env` and
  `apps/node/.env` and restart.
- A token is locked to the first PC that uses it, so a copied token can't
  pretend to be another PC.
- Core only keeps a hash of each token.

The same page lists every browser that's signed in. Sign out one, or "Sign
out all other browsers" if you lose your phone. Logins expire after 30 days.

[Back to the README](../README.md)
