# Home control

Venus can switch lights and plugs, change the TV volume, wake another PC,
and change this PC's volume or lock it. The PC part sends these over your
home Wi-Fi, so it only works at home (or with the PC at home). Add your
devices in **Settings, Home**. Like PC actions, they ask for Approve first
unless you're in Full mode.

**Home Assistant (easiest if you have it).** If you run
[Home Assistant](https://www.home-assistant.io/), Venus can control
everything it knows, whatever the brand: lights, switches, TVs and speakers
(including turning the TV on and off), air-con, and your scenes and scripts.
Apple Home, Google Home and Alexa devices work this way too, once they're in
Home Assistant (they have no API Venus can use directly).

1. In Home Assistant, click your profile (bottom left), then Security, then
   **Long-lived access tokens**, Create token. Copy it (it's shown once).
2. In Venus, Settings, Home, Home Assistant: paste the address you open Home
   Assistant at (like `http://192.168.1.50:8123`) and the token, Connect.
   If `homeassistant.local` doesn't work, use the IP address.
3. Click **Find devices**, tick the ones you want, and change the names to
   what you'll say. Add selected.

Then try `turn on the tv`, `set the aircon to 24`, `set the ac to cool`,
`turn off the bedroom light`, or a scene's name on its own (`movie time`).
Venus only offers lights, switches, fans, TVs and speakers, air-con, scenes
and scripts: never locks, alarms or cameras. Disconnect forgets the token and
the devices you added from Home Assistant.

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
