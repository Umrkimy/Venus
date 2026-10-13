# Home control

Venus can switch lights and plugs, change the TV volume, wake another PC,
and change this PC's volume or lock it. The PC part sends these over your
home Wi-Fi, so it only works at home (or with the PC at home). Add your
devices in **Settings, Home**. Like PC actions, they ask for Approve first
unless you're in Full mode.

**Lights and plugs (Tuya / Smart Life).** Venus talks to them directly on
your Wi-Fi, no cloud needed after setup. It needs each device's id and
"local key", which you get once:

1. Add the bulbs to the Smart Life app like normal.
2. Make a free account on [iot.tuya.com](https://iot.tuya.com), create a
   Cloud project (pick the data center for your region), then under
   Devices, Link App Account, scan the QR code with Smart Life.
3. On the PC, run the wizard and give it the project's Access ID and
   Secret:

   ```bash
   cd apps/node
   .venv/bin/python -m tinytuya wizard        # Windows: .venv\Scripts\python.exe -m tinytuya wizard
   ```

   It lists every device with its id, local key and IP address.
4. In your router, give each bulb a fixed IP so it doesn't change.
5. Settings, Home, Add a device: name it what you'll say ("bedroom light").

**TV (Google / Android TV).** Uses Chromecast, which is built in, so
there's nothing to set up on the TV. Find its IP in the TV's network
settings or your router, give it a fixed IP, and add it as a TV. Venus can
change the volume and mute it; turning the TV on or off isn't there yet.

**Waking a PC.** Turn on Wake-on-LAN in that PC's BIOS and in its network
card settings ("Wake on Magic Packet"), then add it with its MAC address
(`ipconfig /all` on Windows, `ip link` on Linux). Note that Venus runs on
your main PC, so when *that* PC is off nothing can wake it through Venus.
Use a Wake-on-LAN app on your phone (on home Wi-Fi) for that.

**This PC** needs nothing added: `volume up`, `volume 40`, `mute my pc`,
`lock my pc`.

[Back to the README](../README.md)
