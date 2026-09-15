# In-Out Board Roadmap

## UI/UX Revamp
- [x] **Touchscreen & Physical Keyboard Dual Usability**: Check OUT flow supports both physical keyboard shortcuts (`1-7`, `0`, `Enter`, `ESC`, `Y`) and large interactive touch-friendly tiles with key badges.
- [x] **Sub-Second Smartcard Tap & Instant Clock-IN**: APDU UID reading with 1.2s reader debounce and 1.5s API cooldown, preventing freeze/lockouts while allowing rapid deliberate re-taps.
- [x] **Touchscreen Layout Optimization**: 1280x800 resolution containment, background scroll lock, flatpickr touch scaling, and simple-keyboard virtual input.
- [ ] **Personnel Grid View**: Alternative layout option replacing the dense list view with a grid of large square tiles for personnel, making manual touch check-ins faster for high-traffic entryways.

## Admin Panel Mode
- [ ] **On-Device Admin View**: Add an Admin panel/mode accessible directly from the touch display (likely protected by a PIN or admin badge swipe).
  - **Announcement Management**: Ability to update the announcement banner text and title directly from the board. Includes the option to manually input the author's name (or indicate if posting on behalf of someone else).
  - **Quick Pick Customization**: UI to add, change, or remove the quick pick location cards (e.g., Lunch, Appt).
  - **Bot Configuration**: Ability to change the Hermes Telegram Bot onboarding PIN.
  - **User Record Management**: Interface to modify existing user records (e.g., correcting names, ranks, or emails) and completely delete users who no longer work there.
