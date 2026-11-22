"""TC-107 and Addendum D: non-canonical static URLs cannot bypass the photo check.

A WSGI server percent-decodes the URL into PATH_INFO without resolving dot segments.
These tests set PATH_INFO directly, so the test client cannot normalize the path first.
"""

import unittest
from urllib.parse import unquote, urlsplit

from extensions import db
from models import Report, ReportPet
from sprint3_base import Sprint3TestCase

PHOTO = b"\x89PNG\r\n\x1a\nADDENDUM-D-PRIVATE-PHOTO-BYTES"
FILE = "guarded.png"
CANONICAL = f"/static/uploads/{FILE}"
REDIRECTS = (301, 302, 303, 307, 308)
FORMS = (
    "/static/./uploads/{f}",
    "/static/uploads/./{f}",
    "/static/x/../uploads/{f}",
    "/static/x/y/../../uploads/{f}",
    "/static/uploads/x/../{f}",
    "/static/%2e/uploads/{f}",
    "/static/%2E/uploads/{f}",
    "/static/x/%2e%2e/uploads/{f}",
    "/static/x/%2E%2E/uploads/{f}",
    "/static/x/.%2e/uploads/{f}",
    "/static/x/%2e./uploads/{f}",
    "/static/.%2fuploads/{f}",
    "/static/x%2f..%2fuploads%2f{f}",
    "/static//uploads/{f}",
    "/static/uploads//{f}",
    "/static///uploads///{f}",
    "/static/.//uploads/{f}",
    "/static/%2f/uploads/{f}",
    "/static/uploads%2f%2f{f}",
    "/static/uploads\\{f}",
    "/static/.\\uploads\\{f}",
    "/static/x\\..\\uploads\\{f}",
    "/static/uploads%5c{f}",
    "/static/%2e%5cuploads%5c{f}",
    "/static/x%5c..%5cuploads%5c{f}",
)


class UploadPathGuardTests(Sprint3TestCase):
    def setUp(self):
        super().setUp()
        self.login_both()
        (self.upload_dir / FILE).write_bytes(PHOTO)
        self.pet_id = self.seed_pet(name="Guarded Pet", photo_path=f"uploads/{FILE}")

    @staticmethod
    def environ(raw):
        return {"PATH_INFO": unquote(raw), "RAW_URI": raw, "REQUEST_URI": raw}

    def raw_get(self, client, raw):
        return client.open("/", method="GET", environ_overrides=self.environ(raw))

    def fetch(self, client, raw):
        """Follow same-site redirects so a redirect cannot hide a later photo response."""
        response = self.raw_get(client, raw)
        for _hop in range(4):
            if response.status_code not in REDIRECTS:
                break
            target = urlsplit(response.headers["Location"]).path
            if target.startswith("/login"):
                break
            response.close()
            response = self.raw_get(client, target)
        response.direct_passthrough = False
        body = response.get_data()
        status = response.status_code
        response.close()
        return status, body

    def add_report(self, status, shared=True):
        with self.app.app_context():
            report = Report(owner_id=self.user_ids["owner"], status=status, is_shared=shared,
                            last_seen_location="Private synthetic street")
            db.session.add(report)
            db.session.flush()
            db.session.add(ReportPet(report_id=report.id, pet_id=self.pet_id))
            db.session.commit()

    def assert_forms_blocked(self, client, actor):
        for form in FORMS:
            raw = form.format(f=FILE)
            with self.subTest(actor=actor, url=raw):
                status, body = self.fetch(client, raw)
                self.assertNotIn(PHOTO, body, f"{actor} received photo bytes ({status})")
                self.assertLess(status, 500)

    def test_tc_107_raw_request_keeps_non_canonical_path(self):
        for raw, expected in (("/static/./uploads/a.png", "/static/./uploads/a.png"),
                              ("/static/x/%2e%2e/uploads/a.png", "/static/x/../uploads/a.png"),
                              ("/static//uploads/a.png", "/static//uploads/a.png"),
                              ("/static/uploads%5ca.png", "/static/uploads\\a.png")):
            with self.subTest(raw=raw):
                with self.app.test_request_context("/", environ_overrides=self.environ(raw)) as ctx:
                    self.assertEqual(ctx.request.path, expected)

    def test_tc_107_non_canonical_upload_urls_blocked_for_guest(self):
        self.assert_forms_blocked(self.guest, "guest")

    def test_tc_107_non_canonical_upload_urls_blocked_for_other_user(self):
        self.assert_forms_blocked(self.other, "other user")

    def test_tc_107_non_canonical_urls_blocked_on_resolved_shared_report(self):
        for status in ("found", "closed"):
            with self.app.app_context():
                ReportPet.query.delete()
                Report.query.delete()
                db.session.commit()
            self.add_report(status)
            self.assert_forms_blocked(self.guest, f"guest on {status}")
            self.assert_forms_blocked(self.other, f"other user on {status}")

    def test_tc_107_non_canonical_urls_never_error_for_owner(self):
        # The contract does not require these forms to serve; only that any bytes are authorized.
        for form in FORMS:
            raw = form.format(f=FILE)
            with self.subTest(url=raw):
                status, body = self.fetch(self.owner, raw)
                self.assertLess(status, 500)
                if status == 200:
                    self.assertEqual(body, PHOTO)

    def test_tc_107_canonical_url_still_works_for_owner_only(self):
        status, body = self.fetch(self.owner, CANONICAL)
        self.assertEqual((status, body), (200, PHOTO))
        self.assertEqual(self.fetch(self.other, CANONICAL)[0], 404)
        status, body = self.fetch(self.guest, CANONICAL)
        self.assertEqual(status, 302)
        self.assertNotIn(PHOTO, body)

    def test_tc_107_non_upload_static_assets_keep_working(self):
        css_dir = self.upload_dir.parent / "css"
        css_dir.mkdir()
        (css_dir / "site.css").write_bytes(b"body{color:black}")
        (self.upload_dir.parent / "uploads-guide.txt").write_bytes(b"public guide")
        for client in (self.guest, self.other, self.owner):
            for route, expected in (("/static/css/site.css", b"body{color:black}"),
                                    ("/static/uploads-guide.txt", b"public guide")):
                with self.subTest(route=route):
                    self.assertEqual(self.fetch(client, route), (200, expected))


if __name__ == "__main__":
    unittest.main()
