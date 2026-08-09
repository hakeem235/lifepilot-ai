from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import UserProfile

from .models import Note
from .serializers import NoteSerializer


def make_user(auth_id="notes-user", email="notes@example.com"):
    return UserProfile.objects.create(auth_id=auth_id, email=email, timezone="UTC")


class DisplayTitleTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def note(self, **kwargs):
        return Note(user=self.user, **kwargs)

    def test_uses_the_real_title_when_present(self):
        self.assertEqual(self.note(title="  Groceries  ", body="milk").display_title, "Groceries")

    def test_falls_back_to_the_first_non_blank_body_line(self):
        # Quick-captured notes usually have no title; "Untitled" repeated down a
        # list would tell the user nothing about which note is which.
        note = self.note(title="", body="\n\n  Call the bank about the transfer\nthen email Sam")
        self.assertEqual(note.display_title, "Call the bank about the transfer")

    def test_truncates_a_long_first_line(self):
        note = self.note(title="", body="x" * 80)
        self.assertEqual(len(note.display_title), 61)  # 60 chars + ellipsis
        self.assertTrue(note.display_title.endswith("…"))

    def test_empty_note_is_labelled_not_blank(self):
        self.assertEqual(self.note(title="", body="   ").display_title, "Untitled note")


class SerializerValidationTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_rejects_a_wholly_empty_note(self):
        serializer = NoteSerializer(data={"title": "  ", "body": "\n"})
        self.assertFalse(serializer.is_valid())

    def test_accepts_a_body_only_note(self):
        serializer = NoteSerializer(data={"body": "just a thought"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_accepts_a_title_only_note(self):
        serializer = NoteSerializer(data={"title": "Reminder"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_patch_that_would_empty_an_existing_note_is_rejected(self):
        note = Note.objects.create(user=self.user, title="", body="something")
        serializer = NoteSerializer(note, data={"body": "   "}, partial=True)
        self.assertFalse(serializer.is_valid())


class NoteApiTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("other-user", "other@example.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_requires_authentication(self):
        res = APIClient().get(reverse("note-list"))
        self.assertIn(res.status_code, (401, 403))

    def test_create_assigns_the_authenticated_user(self):
        res = self.client.post(reverse("note-list"), {"body": "first note"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Note.objects.get(id=res.data["id"]).user, self.user)

    def test_list_never_leaks_another_users_notes(self):
        Note.objects.create(user=self.other, body="secret")
        mine = Note.objects.create(user=self.user, body="mine")
        res = self.client.get(reverse("note-list"))
        self.assertEqual([n["id"] for n in res.data], [str(mine.id)])

    def test_cannot_fetch_another_users_note_by_id(self):
        theirs = Note.objects.create(user=self.other, body="secret")
        res = self.client.get(reverse("note-detail", args=[theirs.id]))
        self.assertEqual(res.status_code, 404)

    def test_cannot_delete_another_users_note(self):
        theirs = Note.objects.create(user=self.other, body="secret")
        res = self.client.delete(reverse("note-detail", args=[theirs.id]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Note.objects.filter(id=theirs.id).exists())

    def test_pinned_notes_sort_first(self):
        Note.objects.create(user=self.user, body="ordinary")
        pinned = Note.objects.create(user=self.user, body="important", pinned=True)
        res = self.client.get(reverse("note-list"))
        self.assertEqual(res.data[0]["id"], str(pinned.id))

    def test_search_matches_title_and_body_and_excludes_others(self):
        Note.objects.create(user=self.user, title="Dentist", body="book appointment")
        Note.objects.create(user=self.user, title="Shopping", body="milk and bread")
        Note.objects.create(user=self.other, title="Dentist", body="not mine")

        res = self.client.get(reverse("note-list"), {"q": "dentist"})
        self.assertEqual(len(res.data), 1)

        res = self.client.get(reverse("note-list"), {"q": "milk"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Shopping")

    def test_empty_note_is_rejected_by_the_api(self):
        res = self.client.post(reverse("note-list"), {"title": "", "body": ""}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_display_title_is_returned_for_the_list_row(self):
        Note.objects.create(user=self.user, title="", body="pick up parcel")
        res = self.client.get(reverse("note-list"))
        self.assertEqual(res.data[0]["display_title"], "pick up parcel")
