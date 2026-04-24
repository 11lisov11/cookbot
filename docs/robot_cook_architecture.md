# CookBot Robot Cook Architecture

CookBot is recipe-controlled and supervised.

MVP cooking behavior is limited to dry-run, no-heat workflows:

- load YAML recipe;
- run preflight;
- validate safety;
- execute allowed steps through backend and fake Mega;
- pause/abort through ESTOP path.

Full autonomous cooking is out of scope. Any recipe involving heat, blades, raw mains voltage, or unverified workspace geometry must stay locked.

