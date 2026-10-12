> **Superseded:** the live policy is https://medicalapps.homilabs.org/ecg-reader/privacy/ (source: `/mnt/storage/projects/medicalapps_site/tools/build_pages.py`). Edit it there.

# ECG Reader — Privacy Policy (DRAFT for Homi's review)

*HomiLabs · last updated: 12 October 2026*

ECG Reader is a decision-support tool for qualified clinicians. It reads photographs of printed ECGs.
It is built so that **nothing is saved**.

## What the app handles
- **The ECG image you choose.** On your phone it is cropped by you, resized, and stripped of photo metadata
  (location, device, time). It is then sent over an encrypted connection (HTTPS) to our server.
- **Optional clinical details** (age, sex, symptoms, blood pressure, heart rate, SpO₂, known conditions) if you choose to add them.
- **An anonymous, random app ID** created automatically when the app first connects. It is used only to limit
  the number of readings per day. It is not linked to your name, email or phone number.

## What happens to it
- Our server (Google Firebase, region Mumbai) passes the image to an AI service, **Anthropic**, which describes the ECG.
  Our server then applies a fixed rule table and returns the result to your phone.
- **Our server does not store or log the image, the result or the clinical details.** The only thing stored is a
  daily counter for the anonymous app ID, deleted automatically after two days.
- Anthropic processes the image under its commercial API data terms. *(Homi: insert the retention period that applies
  to the HomiLabs Anthropic organisation once confirmed.)*
- On your phone, the result exists only on the result screen. It is discarded when you leave that screen. The app
  keeps no history, no gallery copy and no temporary files.

## What we never do
- No accounts and no login.
- No analytics and no advertising.
- No sale or sharing of data.

## Patient details
Do not photograph or upload patient names, ID numbers or other identifying details. The app asks you to crop the
printed header away before sending.

## Contact
HomiLabs — *(contact email to be added)*
