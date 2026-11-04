# User Manual

**Phase:** Transition | **Status:** Sprint 2 implementation documented; sponsor acceptance _TBD_ | **Owner:** _TBD_ | **Audience:** end users

This manual describes Pet Finder as delivered through Sprint 2 at commit `4d51cc3` on
November 4, 2026. The [Sprint 2 record](../project-management/sprint-2-record.md)
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
4. Use **Log out** in the navigation when you finish.

The navigation provides **My Pets**, **Reports**, and **Contacts**. Messages above the
page explain completed actions or errors. A submitted form with invalid information
stays open and shows the fields to correct.

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

1. Open **Reports**, then **File a report**.
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

## Revision history

| Date | Author | Summary |
|---|---|---|
| _TBD_ | _TBD_ | Initial draft template |
| 2026-11-04 | Codex | Documented delivered Sprint 2 workflows, validation, UTC behavior, generated outputs, flyer excerpt, stale reminder, and troubleshooting. |
