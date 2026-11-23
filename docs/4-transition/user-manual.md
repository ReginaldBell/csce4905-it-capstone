# User Manual

**Phase:** Transition | **Status:** Sprint 2 implementation documented; Sprint 3 tasks merged to `main` through PRs #24 and #25; not deployed; sponsor acceptance _TBD_ | **Owner:** _TBD_ | **Audience:** end users

Sections 1-13 describe Pet Finder as delivered through Sprint 2 at commit `4d51cc3` on
November 4, 2026. Section 14 covers Sprint 3 tasks. The [Sprint 2 record](../project-management/sprint-2-record.md)
contains the implementation decisions, review fixes, and merged pull requests.

## 1. What Pet Finder does

Pet Finder keeps your pet profiles and agency contacts, records missing-pet reports,
tracks report status, and prepares text and a flyer you can use when looking for a pet.
Your account's pet, contact, and report pages are separate from other users' records.

Generated text is built from current saved information when you open it. Pet Finder
does not send an email, make a phone call, or publish a social post for you.

## 2. Getting started

Use a current web browser with JavaScript enabled. JavaScript supplies the timezone for
a last-seen time and powers the Copy and Print controls. Use the address supplied by
the project operator; the deployed address is _TBD_. For the documented local setup,
the address is `http://localhost:5000` after following the
[Maintenance Manual](maintenance-manual.md).

1. Open **Register** if you do not have an account.
2. Enter an email address, a password of at least eight characters, and the same password
   again to confirm it.
3. On later visits, open **Log in** and enter your email and password.
4. Use the **Log out** icon at the top of the page, or **Log out** in **Settings**, when
   you finish.

The navigation provides **Nearby**, **My Pets**, **Reports**, **Contacts**, and
**Settings**. It appears along the bottom on phones and along the left side on larger
screens. Messages above the page explain completed actions or errors. A submitted form
with invalid information stays open and shows the fields to correct.

In **Settings**, **Dark theme**, **Larger text**, and **Search radius** are saved in the
current browser and do not follow you to another device. **Display name** is saved to
your account and appears on your community posts and comments. Printed flyers always
use their standard light layout.

## 3. Maintain pet profiles

1. Open **My Pets**, then choose **Add a pet**.
2. Enter a name and species. Add breed, birth date, notes, and a photo if available.
3. Use a JPG or PNG photo of no more than 5 MB. A birth date cannot be in the future.
4. Save the pet, then open its detail page to view, edit, or delete it.

Uploading a new photo while editing replaces the old photo. Deleting a pet requires a
confirmation page. A deleted pet is removed from any reports that linked to it, but
those reports remain. If a report has no pets left, it can still be viewed; its output
links return to the report with an explanatory message rather than generating an empty
email, script, post, or flyer.

## 4. Maintain agency contacts

1. Open **Contacts**, then **Add a contact**.
2. Enter a category and contact name. Suggested categories include Veterinarian, Animal
   Shelter, Animal Control, Microchip Registry, Groomer, and Other. You can type a
   different category.
3. Enter a phone number, email address, or both. Notes are optional.
4. Save the contact. Open its detail page to edit or delete it; deletion asks for
   confirmation before removing it.

Contacts are grouped by category and sorted alphabetically within each group.
Category is limited to 50 characters and name to 100. An email address must have a
valid format and be no longer than 255 characters. A phone entry must contain at least
one digit and use 7-30 characters from digits, spaces, parentheses, `+`, `-`, or `.`.
Punctuation-only entries such as `-------` are rejected. At least one of phone or email
must be present.

## 5. File a missing-pet report

1. Open **Reports**, then **File a report**. You can also choose **Report missing** on
   a pet's page, which selects that pet for you.
2. Select one or more of your pets. If you have none, Pet Finder takes you to the
   add-pet form first.
3. Enter the required last-seen location, using no more than 255 characters.
4. Optionally enter the last-seen date and time and any notes.
5. Choose **File report**. The new report opens with status **Open**.

Enter the last-seen time in your browser's local timezone. Pet Finder uses the offset
for the selected date, including daylight-saving rules, converts the value to UTC,
and rejects future sightings. The report displays the saved time with a **UTC** label;
it can therefore differ from the local time you entered. Leave the time blank if it is
unknown.

The report detail page lists its pets, last-seen information, full notes, filing time,
current status, history, and output links. The Reports list shows only your reports.

## 6. Update status and read history

1. Open the report from **Reports**.
2. Under **Change status**, choose **Open**, **Found**, or **Closed**.
3. Choose **Update status**.

The History section records the initial filing and later status changes in time order.
You can move between any of the three statuses. Entering Closed records a closure
time; leaving Closed clears that closure time. Submitting the current status displays
an informational message and adds no history entry.

## 7. Prepare an agency email

1. Open the report and choose **Email an agency**.
2. Select one of your contacts. If there are no contacts, use **Add one** first.
3. Review the generated subject and body, which include the pets, last-seen details,
   full report notes, and your account email.
4. Use each **Copy** button to copy the subject or body, or choose **Open in email
   client** to open a draft in your configured email application.
5. Review and send the email yourself in that application.

The email-client link is available only when the selected contact has an email address.
For a phone-only contact, the page explains that no email is on file and still lets you
copy the generated text. Pet Finder does not send or save the generated email.

## 8. Prepare a phone script

1. Open the report and choose **Generate phone script**.
2. Select a contact, adding one first if necessary.
3. Review the script and use **Copy**, or read it during your call.

The script includes the pets, last-seen details, full report notes, and your account
email. The page shows the contact's phone number when one is saved. An email-only
contact can still be selected, but the page states that no phone number is on file.
You place the call yourself.

## 9. Prepare a social post and photos

1. Open the report and choose **Generate social post**. No agency contact is needed.
2. Review the caption, including the pet information, last-seen details, full notes,
   your account email, and hashtags.
3. Use **Copy** to copy the caption.
4. Use **Download photo** for each available pet photo.
5. Paste the text and attach the downloaded photos in your chosen social application.

Pets without photos are named in a note on the page. Pet Finder does not publish the
post. Review what you intend to share, including the report notes and contact email.

## 10. Print a flyer

1. Open the report and choose **Printable flyer**. No agency contact is needed.
2. Review the names, species, last-seen information, notes excerpt, and contact email.
   The flyer uses the first pet with an available photo; it also works without a photo.
3. Choose **Print this flyer** to open the browser's print dialog.
4. Check print preview, select your printer or PDF destination, and print.

Only the flyer's notes are shortened: they contain at most 200 characters, including
an ellipsis when truncated. The saved report notes and the notes shown on report
detail, agency email, phone script, and social post remain in full. Navigation, flash
messages, and the Print/Back controls are hidden in printed output. The long-notes
regression case was verified as one page; use print preview to check your selected
paper size and settings.

## 11. Respond to a stale-pet reminder

After a successful login, Pet Finder displays one reminder if any of your pets have
not been updated for **more than 90 days**. Exactly 90 days does not trigger it. The
message names the affected pets alphabetically and asks you to review their information
and photos.

Open **My Pets** and review those profiles. If a change is needed, edit the pet and
save it. There is no separate reminder acknowledgement button. This reminder appears
at login, not as a background notification, and is not shown when creating a new
account. It considers only your own pets.

## 12. Troubleshooting and questions

| Problem | What to check or do |
|---|---|
| A contact will not save | Correct the inline errors; supply a category, name, and at least one valid phone or email. |
| The report form asks you to add a pet | Add a pet profile before filing a report. |
| A last-seen time is rejected | Check the selected date, local time, browser timezone, and that the sighting is not in the future. |
| A saved time differs from the entered time | Report times display in UTC after conversion from the selected local time. |
| JavaScript is disabled | Enable it before entering local last-seen times. Without a usable timezone offset, the server interprets the entered value as UTC; Copy and Print controls also need JavaScript. |
| Copy does not work | Select the text in the read-only field and copy it manually; browser permissions can affect clipboard access. |
| No email-client button is shown | Add an email address to that contact or copy the generated text. |
| A contact has no phone number | Edit it to add a number, or choose another contact. |
| An output says the report has no pets attached | Its linked pets were deleted. The report remains viewable, but output generation requires at least one linked pet. |
| A photo cannot be downloaded | Confirm a photo is saved on the pet profile. Report a missing-file error to the operator. |
| Flyer notes end with an ellipsis | The flyer uses a 200-character excerpt. Read the report detail page for the full notes. |
| A page says Not Found | The record may be missing or belong to a different account. Sign in to the correct account. |
| A form reports a missing or invalid security token | Reload the form and submit it again from the current signed-in session. |

Generated outputs are not saved as separate documents in Pet Finder. Reopening an
output regenerates it from current report, pet, and contact information. Changes in
Pet Finder do not update copies you already pasted, printed, downloaded, or sent.

## 13. Getting help

Support contact and hours: _TBD_. Include the page, action, message shown, and approximate
time of the problem. Do not include your password.

## 14. Sprint 3 tasks

The tasks in this section are merged to `main` through PRs #24 and #25.
The app is not deployed or sponsor accepted.

### Add more pet details

When you add or edit a pet, you can also enter sex, height in inches, weight in pounds,
colors, markings, and microchip status. If you choose **Chipped**, enter the microchip
number using 9-15 letters or digits. Pet Finder shows the pet's age when a birth date is
saved. Microchip numbers do not appear on community pages.

You can always open your own current pet photo. Another signed-in user can open it only
while it belongs to a report you shared that is still **Open**. After the report is
resolved, other users see *Photo unavailable because this report is resolved.*

### Add a contact address

Add or edit a contact and enter an address of up to 255 characters. You still need a
phone number or email address.

### Edit your account

1. Open **Settings**.
2. Change your display name, full name, phone, or email.
3. If you change your email, enter your current password.
4. Save your changes.

Generated emails, phone scripts, social posts, and flyers show your saved phone along
with your email. Review them before sharing, because anyone who receives them can see
that information. Your phone does not appear on community pages.

### Reset a forgotten password

1. On the login page, choose the forgot-password link.
2. Enter your account email and submit.
3. The page says: *If an account exists for that email, we sent a reset link.*
4. Open the link in the email. It works once and expires after 60 minutes by default.
5. Enter and confirm a new password of at least eight characters, then log in.

If you request another link, use the newest one. Earlier unused links stop working.
Changing your email or finishing a reset also cancels unused links. After a reset, any
other device or browser that was signed in is logged out and must sign in again.

### If sign-in is limited

You can make 5 failed sign-ins for the same email and connection within 15 minutes. The
6th attempt shows *Too many attempts. Try again later.*, even if the password is correct.
Wait 15 minutes and try again. Password reset
requests are limited to 3 per hour; extra requests show the normal message but do not
send another email.

### Pending account and comment fixes

These fixes are awaiting integration and verification, so they may not be in the version
you are using:

- Registration will show a field error for an email address that is too long.
- A very small pet measurement will keep its exact decimal value when you edit the pet.
- If a report stops being shared, you will be able to delete your own comment from
  **Your comments on unshared reports** on the community page. Other people still cannot
  see that post or its comments.

### Sprint 3 troubleshooting

| Problem | What to do |
|---|---|
| No reset email arrives | Check spam and the address you entered. Wait before trying again, because extra requests do not send email. Contact the operator if it still does not arrive. |
| *This reset link is invalid or has expired.* | Request a new link and use the newest email. |
| *Too many attempts. Try again later.* | Wait up to 15 minutes, or reset your password from the same connection. |
| You were logged out on another device | This is expected after a password reset. Sign in with the new password. If you did not reset it, reset it now and contact the operator. |
| Email change is rejected | Check the current password, the email format, and whether another account uses that email. |
| Microchip number is rejected | Choose **Chipped** and use 9-15 letters or digits. |

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | IT Capstone Team (B) | Documented delivered Sprint 2 workflows, validation, UTC behavior, generated outputs, flyer excerpt, stale reminder, and troubleshooting. |
| 2026-11-21 | IT Capstone Team (B) | Documented the Material 3 navigation, Settings, and Report missing shortcut on the unmerged UI branch. |
| 2026-11-21 | IT Capstone Team (B) | Add pet detail, contact address, account, password reset, and sign-in limit tasks, implemented on `sprint3/integration`, not merged. |
| 2026-11-21 | IT Capstone Team (B) | Apply contract Addenda A and B: photo visibility, canceled links, and logout after reset, implemented on `sprint3/integration`, not merged. |
| 2026-11-21 | IT Capstone Team (B) | Apply integration corrections and contract Addenda C and D: sixth-attempt limit and resolved photo message, implemented on `sprint3/integration`, not merged. |
| 2026-11-22 | IT Capstone Team (B) | Replace pending Sprint 3 status with recorded automated, QA, and owner-check evidence. |
| 2026-11-22 | IT Capstone Team (B) | Note pending registration, measurement, and comment deletion fixes. |
| 2026-11-22 | IT Capstone Team (B) | Record Sprint 3 as merged through PRs #24 and #25, not deployed or sponsor accepted, with P1-P11 still pending. Add the P7 entry point. |
