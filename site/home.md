The homelab's standard operating procedures: what gets done by hand, on a trigger, and is too easy
to get wrong from memory. It is published on GitHub Pages, so it stays up when the homelab
doesn't. Each card is a checklist: tick the steps as you go, and the page remembers them for a
day.

!!! danger "Memory items"
    1. The homelab is down and you are reading this: GitHub is up. Start at the **Emergency** tab.
    2. Roboform holds what no machine does: the ansible-vault passphrase, the OpenBao Shamir
       recovery keys (3 of 5) and the age key that decrypts the backups.
    3. Every runbook's source is public: `git clone https://github.com/pvginkel/Ansible`.
    4. Keep the offline copy (bottom of every page) on a laptop, for the day GitHub is down too.
