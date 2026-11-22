"""NF2: new private pet, contact, and account fields stay off community pages."""

import unittest

from extensions import db
from models import Pet, Report, ReportPet
from sprint3_base import Sprint3TestCase


class CommunityPrivacyTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.login_both()
        self.update = self.fixtures["users"]["account_update"]
        saved = self.post(self.owner, "/settings", {
            "display_name": self.update["display_name"],
            "full_name": self.update["full_name"],
            "phone": self.update["phone"],
            "email": self.users["owner"]["email"],
            "current_password": "",
        })
        self.assertEqual(saved.status_code, 302)
        created = self.post(self.owner, "/pets/new", self.pet_values("full_profile"))
        self.assertEqual(created.status_code, 302)
        self.pet_id = int(created.headers["Location"].rsplit("/", 1)[-1])
        contact = self.post(self.owner, "/contacts/new", self.contact_values("vet_full"))
        self.assertEqual(contact.status_code, 302)
        with self.app.app_context():
            report = Report(owner_id=self.user_ids["owner"], status="open",
                            last_seen_location="Private synthetic street")
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=self.pet_id))
            db.session.commit()
            self.report_id = report.id
        self.post_url = f"/community/reports/{self.report_id}"
        shared = self.post(self.owner, f"{self.post_url}/share", {
            "display_name": "Neighborhood helper",
            "community_area": "North Park",
            "community_description": "Please share sightings.",
            "latitude": "33.21",
            "longitude": "-97.13",
            "confirm_sharing": "yes",
        })
        self.assertEqual(shared.status_code, 302)

    def private_values(self):
        row = self.pets["full_profile"]
        return {
            "microchip_number": row["microchip_number"],
            "markings": row["markings"],
            "colors": row["colors"],
            "height_inches": str(row["height_inches"]),
            "weight_lbs": str(row["weight_lbs"]),
            "owner_phone": self.update["phone"],
            "owner_full_name": self.update["full_name"],
            "owner_email": self.users["owner"]["email"],
            "contact_address": self.contacts["vet_full"]["address"],
        }

    def community_pages(self):
        search = {"latitude": "33.21", "longitude": "-97.13", "radius": "10"}
        return {
            "feed_neighbor": self.other.get("/community", query_string=search),
            "detail_neighbor": self.other.get(self.post_url),
            "feed_owner": self.owner.get("/community", query_string=search),
            "detail_owner": self.owner.get(self.post_url),
        }

    def test_new_private_fields_are_absent_from_community_pages(self):
        pages = self.community_pages()
        self.assertIn(self.pets["full_profile"]["name"], self.page_text(pages["detail_neighbor"]))
        for page_name, response in pages.items():
            self.assertEqual(response.status_code, 200, page_name)
            text = self.page_text(response)
            for field, value in self.private_values().items():
                if page_name.endswith("owner") and field == "owner_email":
                    continue  # The signed-in owner's own navigation may show their email.
                with self.subTest(page=page_name, field=field):
                    self.assertNotIn(value, text)

    def test_guest_cannot_read_new_private_fields(self):
        for route in ("/community", self.post_url):
            with self.subTest(route=route):
                response = self.guest.get(route)
                text = self.page_text(response)
                for field, value in self.private_values().items():
                    self.assertNotIn(value, text, field)

    def test_other_user_cannot_open_private_pet_page_after_sharing(self):
        self.assertEqual(self.other.get(f"/pets/{self.pet_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
